"""Transparent, deterministic community-priority scoring and allocation."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from healthcare_di.config import INTERVENTION_COSTS


def percentile(series: pd.Series, *, reverse: bool = False) -> pd.Series:
    """Map a measure to 0-100 using rank percentiles, preserving ties."""
    values = pd.to_numeric(series, errors="coerce")
    filled = values.fillna(values.median())
    ranks = filled.rank(method="average", ascending=not reverse)
    denominator = max(len(filled) - 1, 1)
    return ((ranks - 1) / denominator * 100).clip(0, 100)


def _weighted_score(frame: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    return sum(percentile(frame[column]) * weight for column, weight in weights.items())


def _recommended_action(row: pd.Series) -> str:
    domains = {
        "health": row["health_burden_score"],
        "sdoh": row["sdoh_score"],
        "access": row["access_score"],
        "quality": row["hospital_gap_score"],
    }
    driver = max(domains, key=domains.get)
    if driver == "access" or row["transportation_barrier_rate"] >= 12:
        return "Deploy mobile clinic and transportation outreach"
    if driver == "sdoh" and row["uninsured_rate"] >= 18:
        return "Launch benefits navigation and enrollment campaign"
    if row["poor_mental_health_rate"] >= 18:
        return "Expand community behavioral health outreach"
    if driver == "quality":
        return "Form hospital quality and referral partnership"
    return "Target chronic disease prevention and care coordination"


def _driver_summary(row: pd.Series) -> str:
    domains = {
        "health burden": row["health_burden_score"],
        "social need": row["sdoh_score"],
        "care access": row["access_score"],
        "hospital gap": row["hospital_gap_score"],
    }
    leaders = sorted(domains, key=domains.get, reverse=True)[:2]
    return f"{leaders[0].title()} and {leaders[1]}"


def build_priority_mart(
    places: pd.DataFrame,
    hospitals: pd.DataFrame,
    census: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join public sources and calculate leadership-friendly domain scores."""
    health = places.copy()
    health["county_key"] = health["county_name"].str.upper().str.replace(" ", "", regex=False)
    merged = health.merge(hospitals, on="county_key", how="left")
    if census is not None:
        acs = census.copy()
        acs["county_fips"] = acs["county_fips"].astype(str).str.zfill(5)
        merged = merged.merge(
            acs[["county_fips", "median_household_income", "poverty_rate"]],
            on="county_fips",
            how="left",
        )
    else:
        merged["median_household_income"] = pd.NA
        merged["poverty_rate"] = pd.NA
    count_columns = [
        "hospital_count",
        "rated_hospital_count",
        "emergency_hospital_count",
        "birthing_friendly_count",
    ]
    merged[count_columns] = merged[count_columns].fillna(0).astype(int)
    merged["hospitals_per_100k"] = (
        merged["hospital_count"] / merged["population"].clip(lower=1) * 100_000
    )

    merged["health_burden_score"] = _weighted_score(
        merged,
        {
            "obesity_rate": 0.25,
            "diabetes_rate": 0.25,
            "hypertension_rate": 0.20,
            "poor_physical_health_rate": 0.15,
            "poor_mental_health_rate": 0.15,
        },
    )
    merged["low_income_score"] = percentile(merged["median_household_income"], reverse=True)
    merged["sdoh_score"] = (
        percentile(merged["food_insecurity_rate"]) * 0.30
        + percentile(merged["uninsured_rate"]) * 0.25
        + percentile(merged["poverty_rate"]) * 0.30
        + merged["low_income_score"] * 0.15
    )
    merged["access_score"] = (
        percentile(merged["transportation_barrier_rate"]) * 0.40
        + percentile(merged["annual_checkup_rate"], reverse=True) * 0.25
        + percentile(merged["hospitals_per_100k"], reverse=True) * 0.35
    )

    rating_gap = ((5 - merged["average_hospital_rating"]) / 4 * 100).clip(0, 100)
    # Missing ratings indicate uncertainty, not proof of poor quality.
    merged["hospital_gap_score"] = rating_gap.fillna(60)
    merged["rating_data_status"] = merged["average_hospital_rating"].apply(
        lambda value: "Available" if pd.notna(value) else "Insufficient rating data"
    )
    merged["total_priority_score"] = (
        merged["health_burden_score"] * 0.35
        + merged["sdoh_score"] * 0.25
        + merged["access_score"] * 0.25
        + merged["hospital_gap_score"] * 0.15
    ).round(1)
    merged["priority_tier"] = pd.cut(
        merged["total_priority_score"],
        bins=[-1, 40, 60, 75, 101],
        labels=["Monitor", "Elevated", "High", "Critical"],
    ).astype(str)
    merged["recommended_action"] = merged.apply(_recommended_action, axis=1)
    merged["primary_drivers"] = merged.apply(_driver_summary, axis=1)
    merged["rank"] = merged["total_priority_score"].rank(
        method="first", ascending=False
    ).astype(int)
    return merged.sort_values("rank").reset_index(drop=True)


def simulate_allocation(
    mart: pd.DataFrame,
    budget: int,
    intervention: str,
    max_communities: int = 15,
) -> pd.DataFrame:
    """Allocate equal intervention units greedily by priority score."""
    if intervention not in INTERVENTION_COSTS:
        raise ValueError(f"Unknown intervention: {intervention}")
    unit_cost = INTERVENTION_COSTS[intervention]
    units = min(max(budget // unit_cost, 0), max_communities, len(mart))
    selected = mart.nlargest(units, "total_priority_score").copy()
    selected["intervention"] = intervention
    selected["allocated_budget"] = unit_cost
    selected["estimated_people_reached"] = (
        (selected["population"] * 0.02).clip(lower=250, upper=5000).round().astype(int)
    )
    return selected[
        [
            "rank",
            "county_name",
            "total_priority_score",
            "primary_drivers",
            "intervention",
            "allocated_budget",
            "estimated_people_reached",
        ]
    ]

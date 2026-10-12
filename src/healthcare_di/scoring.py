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


DOMAIN_WEIGHTS = {
    "health_burden_score": ("Health burden", 0.35),
    "sdoh_score": ("Social need", 0.25),
    "access_score": ("Care access", 0.25),
    "hospital_gap_score": ("Hospital gap", 0.15),
}


def action_decision(row: pd.Series) -> tuple[str, str]:
    """Return the action and its first matching rule from one decision path."""
    driver = max(DOMAIN_WEIGHTS, key=lambda column: row[column])
    transport = row["transportation_barrier_rate"]
    if driver == "access_score" or transport >= 12:
        reasons = []
        if transport >= 12:
            reasons.append(
                f"Transportation barrier rate {transport:.1f}% meets the >=12% threshold"
            )
        if driver == "access_score":
            reasons.append("Care access is the highest unweighted domain score")
        return "Deploy mobile clinic and transportation outreach", "; ".join(reasons) + "."
    if driver == "sdoh_score" and row["uninsured_rate"] >= 18:
        return (
            "Launch benefits navigation and enrollment campaign",
            f"Social need is the highest unweighted domain score and uninsured rate "
            f"{row['uninsured_rate']:.1f}% meets the >=18% threshold.",
        )
    if row["poor_mental_health_rate"] >= 18:
        return (
            "Expand community behavioral health outreach",
            f"Poor mental health rate {row['poor_mental_health_rate']:.1f}% meets "
            "the >=18% threshold; earlier rules did not match.",
        )
    if driver == "hospital_gap_score":
        return (
            "Form hospital quality and referral partnership",
            "Hospital gap is the highest unweighted domain score; earlier rules did not match.",
        )
    return (
        "Target chronic disease prevention and care coordination",
        "Fallback action: none of the earlier transportation, enrollment, mental health, "
        "or hospital-gap rules matched.",
    )


def explain_priority_mart(mart: pd.DataFrame) -> pd.DataFrame:
    """Add explanations to both rebuilt and previously saved marts."""
    result = mart.copy()
    for column, (_, weight) in DOMAIN_WEIGHTS.items():
        result[column.replace("_score", "_contribution")] = result[column] * weight
    decisions = result.apply(action_decision, axis=1)
    result["recommended_action"] = decisions.map(lambda decision: decision[0])
    result["action_reason"] = decisions.map(lambda decision: decision[1])
    result["primary_drivers"] = result.apply(
        lambda row: " and ".join(
            DOMAIN_WEIGHTS[column][0]
            for column in sorted(
                DOMAIN_WEIGHTS,
                key=lambda column: row[column] * DOMAIN_WEIGHTS[column][1],
                reverse=True,
            )[:2]
        ),
        axis=1,
    )
    return result


def rating_sensitivity(mart: pd.DataFrame) -> pd.DataFrame:
    """Compare ranks across missing-rating assumptions, keeping other inputs fixed."""
    result = (
        mart[["county_name", "rank", "total_priority_score"]]
        .rename(
            columns={
                "rank": "Baseline rank",
                "total_priority_score": "Baseline score",
                "county_name": "County",
            }
        )
        .copy()
    )
    missing = mart["average_hospital_rating"].isna()
    base = sum(mart[column] * weight for column, (_, weight) in DOMAIN_WEIGHTS.items())
    without_rating = base - mart["hospital_gap_score"] * 0.15
    for label, score in {
        "Missing = 50": base.where(~missing, without_rating + 50 * 0.15),
        "Exclude missing domain": base.where(~missing, without_rating / 0.85),
    }.items():
        score = score.round(1)
        # County-source order matches baseline tie-breaking (county FIPS order).
        ordered = score.loc[mart.sort_values("county_fips").index]
        ranks = ordered.rank(method="first", ascending=False).astype(int)
        result[f"{label}: score"] = score
        result[f"{label}: rank"] = ranks
    result["Missing rating"] = missing
    return result


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
    merged = explain_priority_mart(merged)
    merged["rank"] = (
        merged["total_priority_score"].rank(method="first", ascending=False).astype(int)
    )
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

from pathlib import Path

import pandas as pd
import pytest

from healthcare_di.ingestion import normalize_cdc
from healthcare_di.quality import assert_quality, validate_priority_mart
from healthcare_di.scoring import build_priority_mart, percentile, simulate_allocation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def mart() -> pd.DataFrame:
    places = normalize_cdc(pd.read_csv(ROOT / "data/snapshots/cdc_places_az_2025.csv", dtype=str))
    hospitals = pd.read_csv(ROOT / "data/snapshots/cms_hospitals_az_2026.csv")
    census = pd.read_csv(ROOT / "data/snapshots/census_acs_az_2024.csv", dtype={"county_fips": str})
    return build_priority_mart(places, hospitals, census)


def test_percentile_is_bounded_and_monotonic() -> None:
    result = percentile(pd.Series([1, 2, 3]))
    assert result.tolist() == [0.0, 50.0, 100.0]


def test_priority_mart_passes_contract(mart: pd.DataFrame) -> None:
    assert_quality(mart)
    assert len(mart) == 15
    assert mart["rank"].tolist() == list(range(1, 16))
    assert mart["total_priority_score"].between(0, 100).all()


def test_missing_rating_is_exposed_as_uncertainty(mart: pd.DataFrame) -> None:
    apache = mart.loc[mart["county_name"].eq("Apache")].iloc[0]
    assert apache["rating_data_status"] == "Insufficient rating data"
    assert apache["hospital_gap_score"] == 60


def test_allocation_never_overspends(mart: pd.DataFrame) -> None:
    allocation = simulate_allocation(mart, 250_000, "Mobile clinic day", max_communities=4)
    assert len(allocation) == 4
    assert allocation["allocated_budget"].sum() <= 250_000
    assert allocation["total_priority_score"].is_monotonic_decreasing


def test_allocation_rejects_unknown_intervention(mart: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Unknown intervention"):
        simulate_allocation(mart, 100_000, "Teleportation")


def test_quality_results_are_all_green(mart: pd.DataFrame) -> None:
    assert all(result.passed for result in validate_priority_mart(mart))


def test_action_reason_uses_trigger_not_top_contribution(mart: pd.DataFrame) -> None:
    apache = mart.loc[mart["county_name"].eq("Apache")].iloc[0]
    assert "19.5%" in apache["action_reason"]
    assert ">=12%" in apache["action_reason"]
    assert apache["primary_drivers"] == "Health burden and Social need"
    assert round(apache["health_burden_contribution"], 1) == 28.7
    assert round(apache["sdoh_contribution"], 1) == 22.3


def test_rating_sensitivity_keeps_observed_scores_and_reweights_missing(mart: pd.DataFrame) -> None:
    from healthcare_di.scoring import rating_sensitivity

    comparison = rating_sensitivity(mart)
    observed = mart["average_hospital_rating"].notna()
    for label in ["Missing = 50", "Exclude missing domain"]:
        assert comparison.loc[observed, f"{label}: score"].equals(
            comparison.loc[observed, "Baseline score"]
        )
        assert set(comparison[f"{label}: rank"]) == set(range(1, 16))
    apache = mart.loc[mart["county_name"].eq("Apache")].iloc[0]
    idx = apache.name
    expected = (
        apache["health_burden_score"] * 0.35
        + apache["sdoh_score"] * 0.25
        + apache["access_score"] * 0.25
    ) / 0.85
    assert comparison.loc[idx, "Exclude missing domain: score"] == round(expected, 1)
    assert comparison.loc[idx, "Missing = 50: score"] == 73.6


@pytest.mark.parametrize(
    ("overrides", "action", "reason"),
    [
        ({"transportation_barrier_rate": 12}, "Deploy mobile", "12.0%"),
        ({"access_score": 95}, "Deploy mobile", "Care access"),
        ({"sdoh_score": 95, "uninsured_rate": 18}, "Launch benefits", "18.0%"),
        ({"poor_mental_health_rate": 18}, "Expand community", "18.0%"),
        ({"hospital_gap_score": 95}, "Form hospital", "Hospital gap"),
        ({}, "Target chronic", "Fallback"),
        (
            {"transportation_barrier_rate": 12, "poor_mental_health_rate": 25},
            "Deploy mobile",
            "12.0%",
        ),
    ],
)
def test_action_rules_and_reasons_share_order(overrides, action, reason) -> None:
    from healthcare_di.scoring import action_decision

    row = pd.Series(
        {
            "health_burden_score": 80,
            "sdoh_score": 60,
            "access_score": 50,
            "hospital_gap_score": 40,
            "transportation_barrier_rate": 11.9,
            "uninsured_rate": 17.9,
            "poor_mental_health_rate": 17.9,
        }
    )
    row.update(pd.Series(overrides, dtype=float))
    selected, explanation = action_decision(row)
    assert selected.startswith(action)
    assert reason in explanation

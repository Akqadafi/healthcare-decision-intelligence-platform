from pathlib import Path

import pandas as pd
import pytest

from healthcare_di.ingestion import normalize_cdc
from healthcare_di.quality import assert_quality, validate_priority_mart
from healthcare_di.scoring import build_priority_mart, percentile, simulate_allocation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def mart() -> pd.DataFrame:
    places = normalize_cdc(
        pd.read_csv(ROOT / "data/snapshots/cdc_places_az_2025.csv", dtype=str)
    )
    hospitals = pd.read_csv(ROOT / "data/snapshots/cms_hospitals_az_2026.csv")
    census = pd.read_csv(
        ROOT / "data/snapshots/census_acs_az_2024.csv", dtype={"county_fips": str}
    )
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

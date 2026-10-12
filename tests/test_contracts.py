from pathlib import Path

import pandas as pd
import pytest

from healthcare_di.ingestion import aggregate_cms, normalize_cdc
from healthcare_di.pipeline import build, load_snapshots
from healthcare_di.quality import assert_quality, validate_priority_mart
from healthcare_di.scoring import build_priority_mart, percentile


@pytest.mark.parametrize(
    "column,value",
    [
        ("population", -1),
        ("population", 1.5),
        ("population", float("inf")),
        ("uninsured_rate", 101),
        ("obesity_rate", -1),
        ("diabetes_rate", None),
        ("county_fips", "06001"),
    ],
)
def test_invalid_source_values_fail_before_scoring(column, value):
    places, hospitals, census = load_snapshots()
    places[column] = places[column].astype(object)
    places.loc[0, column] = value
    with pytest.raises(ValueError, match="contract"):
        build_priority_mart(places, hospitals, census)


@pytest.mark.parametrize("source", [0, 1, 2])
def test_duplicate_source_keys_fail(source):
    inputs = list(load_snapshots())
    inputs[source] = pd.concat([inputs[source], inputs[source].iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_priority_mart(*inputs)


def test_missing_required_mart_column_reports_failure():
    mart = build_priority_mart(*load_snapshots()).drop(columns="county_fips")
    results = validate_priority_mart(mart)
    assert results[0].check == "required_columns" and not results[0].passed
    with pytest.raises(ValueError, match="county_fips"):
        assert_quality(mart)


def test_negative_mart_population_fails():
    mart = build_priority_mart(*load_snapshots())
    mart.loc[0, "population"] = -1
    with pytest.raises(ValueError, match="positive_integer_population"):
        assert_quality(mart)


def test_census_is_required_and_all_missing_metric_fails():
    places, hospitals, census = load_snapshots()
    with pytest.raises(ValueError, match="Census input is required"):
        build_priority_mart(places, hospitals)
    census["poverty_rate"] = float("nan")
    with pytest.raises(ValueError, match="entirely missing"):
        build_priority_mart(places, hospitals, census)
    with pytest.raises(ValueError, match="entirely missing"):
        percentile(pd.Series([None, None]))


def test_partial_census_missingness_uses_documented_median():
    places, hospitals, census = load_snapshots()
    census.loc[0, "poverty_rate"] = float("nan")
    mart = build_priority_mart(places, hospitals, census)
    assert mart["total_priority_score"].notna().all()
    assert_quality(mart)


def test_missing_county_and_unknown_hospital_join_fail():
    places, hospitals, census = load_snapshots()
    with pytest.raises(ValueError, match="15 Arizona"):
        build_priority_mart(places.iloc[1:], hospitals, census)
    hospitals.loc[0, "county_key"] = "UNKNOWN"
    with pytest.raises(ValueError, match="match Arizona"):
        build_priority_mart(places, hospitals, census)


def test_raw_missing_columns_fail_clearly():
    with pytest.raises(ValueError, match="missing columns"):
        normalize_cdc(pd.DataFrame())
    with pytest.raises(ValueError, match="missing columns"):
        aggregate_cms(pd.DataFrame())


def test_live_build_cannot_overwrite_bundled_outputs():
    from healthcare_di.config import GOLD_DIR

    with pytest.raises(ValueError, match="separate"):
        build(live=True, output_dir=GOLD_DIR)


def test_build_produces_validated_outputs(tmp_path: Path):
    mart = build(output_dir=tmp_path)
    assert_quality(mart)
    assert (tmp_path / "data_quality_report.csv").exists()


def test_nonnumeric_score_reports_quality_failure():
    mart = build_priority_mart(*load_snapshots())
    mart["total_priority_score"] = mart["total_priority_score"].astype(object)
    mart.loc[0, "total_priority_score"] = "bad"
    with pytest.raises(ValueError, match="score_range"):
        assert_quality(mart)

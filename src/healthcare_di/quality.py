"""Small, explicit data-quality checks suitable for CI and audit evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    observed: str


def validate_priority_mart(frame: pd.DataFrame) -> list[CheckResult]:
    required = {
        "county_fips",
        "county_name",
        "population",
        "total_priority_score",
        "recommended_action",
    }
    results = [
        CheckResult("required_columns", required.issubset(frame.columns), str(sorted(required))),
        CheckResult("row_count", len(frame) == 15, f"{len(frame)} Arizona counties"),
        CheckResult(
            "unique_county_fips",
            frame["county_fips"].nunique() == len(frame),
            f"{frame['county_fips'].nunique()} unique values",
        ),
        CheckResult(
            "valid_fips",
            frame["county_fips"].astype(str).str.fullmatch(r"\d{5}").all(),
            "five-digit strings",
        ),
        CheckResult(
            "score_range",
            frame["total_priority_score"].between(0, 100).all(),
            f"{frame['total_priority_score'].min()}-{frame['total_priority_score'].max()}",
        ),
        CheckResult(
            "non_null_recommendations",
            frame["recommended_action"].notna().all(),
            f"{frame['recommended_action'].isna().sum()} nulls",
        ),
    ]
    return results


def quality_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(asdict(result) for result in validate_priority_mart(frame))


def assert_quality(frame: pd.DataFrame) -> None:
    failed = [result for result in validate_priority_mart(frame) if not result.passed]
    if failed:
        detail = "; ".join(f"{item.check}: {item.observed}" for item in failed)
        raise ValueError(f"Data quality checks failed: {detail}")

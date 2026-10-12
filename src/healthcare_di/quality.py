"""Small, explicit data-quality checks suitable for CI and audit evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from healthcare_di.contracts import ARIZONA_FIPS


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
    missing = sorted(required - set(frame.columns))
    if missing:
        return [CheckResult("required_columns", False, f"missing: {missing}")]
    scores = pd.to_numeric(frame["total_priority_score"], errors="coerce")
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
            scores.between(0, 100).all(),
            f"{scores.min()}-{scores.max()}",
        ),
        CheckResult(
            "non_null_recommendations",
            frame["recommended_action"].notna().all(),
            f"{frame['recommended_action'].isna().sum()} nulls",
        ),
    ]
    population = pd.to_numeric(frame["population"], errors="coerce")
    results.extend(
        [
            CheckResult(
                "positive_integer_population",
                bool((np.isfinite(population) & (population >= 1) & (population % 1 == 0)).all()),
                "finite positive integers",
            ),
            CheckResult(
                "arizona_county_set",
                set(frame["county_fips"]) == ARIZONA_FIPS,
                "exactly the 15 Arizona county identifiers",
            ),
        ]
    )
    for column in frame.columns:
        if column.endswith("_rate"):
            values = pd.to_numeric(frame[column], errors="coerce")
            results.append(
                CheckResult(
                    f"range_{column}",
                    bool(
                        (values.dropna() if column == "poverty_rate" else values)
                        .between(0, 100)
                        .all()
                    ),
                    "finite percentages in [0, 100]",
                )
            )
    return results


def quality_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(asdict(result) for result in validate_priority_mart(frame))


def assert_quality(frame: pd.DataFrame) -> None:
    failed = [result for result in validate_priority_mart(frame) if not result.passed]
    if failed:
        detail = "; ".join(f"{item.check}: {item.observed}" for item in failed)
        raise ValueError(f"Data quality checks failed: {detail}")

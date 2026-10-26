import csv
from dataclasses import replace
from pathlib import Path

import pytest

from healthcare_di import workbench as wb

FIXTURES = Path(__file__).resolve().parents[1] / "examples/workbench-pilot"


@pytest.fixture
def inputs():
    context = list(csv.DictReader((FIXTURES / "context_SYNTHETIC.csv").open(encoding="utf-8")))
    content = (FIXTURES / "outreach_SYNTHETIC.csv").read_bytes()
    study = wb.Study(tuple(row["county_fips"] for row in context), "2025-01", "Demo outreach")
    return content, context, study


def test_expected_results_and_missingness(inputs):
    result = wb.compare_contacts(*inputs)
    assert [r["contacts_per_1000"] for r in result["results"]] == [1, 4, 0, None]
    assert [r["investigate"] for r in result["results"]] == [True, False, True, None]
    assert result["counts"] == dict(
        uploaded=3,
        matched=3,
        rejected=0,
        context_only=1,
        classifiable=3,
        unclassifiable=1,
        flagged=2,
    )
    assert result["results"][-1]["reasons"] == ["missing_service_record"]
    assert len(result["input_sha256"]) == 64


@pytest.mark.parametrize("value", ["-1", "1.5", "", "NaN", "inf", "1e2", "9" * 16])
def test_bad_contacts_block_whole_upload(inputs, value):
    content, _, study = inputs
    content = content.replace(b"outreach,10", f"outreach,{value}".encode())
    with pytest.raises(wb.ValidationError) as caught:
        wb.parse_contacts(content, study)
    assert caught.value.issues[0].row == 2
    assert caught.value.issues[0].field == "contacts"


@pytest.mark.parametrize(
    "old,new,field",
    [
        (b"04001", b"06001", "county_fips"),
        (b"04001", b"4001", "county_fips"),
        (b"2025-01", b"2025-13", "reporting_month"),
        (b"Demo outreach", b"Other program", "program"),
    ],
)
def test_scope_errors(inputs, old, new, field):
    content, _, study = inputs
    with pytest.raises(wb.ValidationError) as caught:
        wb.parse_contacts(content.replace(old, new), study)
    assert any(issue.field == field for issue in caught.value.issues)


def test_duplicate_does_not_sum(inputs):
    content, _, study = inputs
    with pytest.raises(wb.ValidationError, match="Duplicate key"):
        wb.parse_contacts(content + b"04001,2025-01,Demo outreach,15\n", study)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"\xff",
        b"a,b\n1,2",
        b"\x00",
        b'county_fips,reporting_month,program,contacts\n"unclosed',
        b"county_fips,reporting_month,program,contacts\n04001,2025-01,x,2,extra",
        b"county_fips,reporting_month,program,contacts\n",
        b"county_fips,county_fips,program,contacts\n",
    ],
)
def test_invalid_files(inputs, content):
    with pytest.raises(wb.ValidationError):
        wb.parse_contacts(content, inputs[2])


def test_size_and_row_limits(inputs, monkeypatch):
    content, _, study = inputs
    monkeypatch.setattr(wb, "MAX_BYTES", len(content) - 1)
    with pytest.raises(wb.ValidationError, match="exceeds"):
        wb.parse_contacts(content, study)
    monkeypatch.setattr(wb, "MAX_BYTES", len(content))
    monkeypatch.setattr(wb, "MAX_ROWS", 2)
    with pytest.raises(wb.ValidationError, match="Too many"):
        wb.parse_contacts(content, study)


def test_period_review_preserved(inputs):
    content, context, study = inputs
    context[0]["observation_month"] = "2024-01"
    with pytest.raises(ValueError, match="rationale"):
        wb.compare_contacts(content, context, study)
    result = wb.compare_contacts(
        content, context, replace(study, period_rationale="Historical context")
    )
    assert result["period_rationale"] == "Historical context"
    assert result["observation_months"] == ["2024-01", "2025-01"]


@pytest.mark.parametrize("population", [0, -1, "", None, "inf", 1.5])
def test_invalid_denominator_never_classifies(inputs, population):
    content, context, study = inputs
    context[0]["resident_population"] = population
    row = wb.compare_contacts(content, context, study)["results"][0]
    assert row["contacts_per_1000"] is None
    assert row["investigate"] is None
    assert "invalid_population" in row["reasons"]


def test_threshold_boundaries_and_changes(inputs):
    content, context, study = inputs
    context[0]["need_percent"] = 20
    content = content.replace(b"outreach,10", b"outreach,20")
    assert wb.compare_contacts(content, context, study)["results"][0]["investigate"] is False
    result = wb.compare_contacts(content, context, replace(study, activity_threshold=2.01))
    assert result["results"][0]["investigate"] is True
    assert result["thresholds"]["activity_below"] == 2.01


def test_context_cardinality(inputs):
    content, context, study = inputs
    with pytest.raises(ValueError, match="exactly one"):
        wb.compare_contacts(content, context + [context[0]], study)
    with pytest.raises(ValueError, match="exactly one"):
        wb.compare_contacts(content, context[:-1], study)


@pytest.mark.parametrize(
    "changes",
    [
        dict(month="2025-13"),
        dict(counties=()),
        dict(counties=("06001",)),
        dict(program=""),
        dict(need_threshold=101),
        dict(activity_threshold=float("nan")),
    ],
)
def test_invalid_study(inputs, changes):
    with pytest.raises(ValueError):
        replace(inputs[2], **changes)

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from healthcare_di.workbench import Study, compare_contacts
from healthcare_di.workbench_io import export_csv, map_upload, package, read_upload

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/workbench-pilot"


def inputs():
    raw = (EXAMPLES / "outreach_SYNTHETIC.csv").read_bytes()
    with (EXAMPLES / "context_SYNTHETIC.csv").open() as handle:
        context = list(csv.DictReader(handle))
    return raw, context, Study(tuple(row["county_fips"] for row in context),
                               "2025-01", "Demo outreach")


def test_mapping_preserves_ids_and_accounts_for_rows():
    raw = b"county,date,service,count,unused\n04001,2025-01,Demo outreach,10,anything\n"
    header, rows = read_upload(raw)
    mapping = dict(county_fips="county", reporting_month="date",
                   program="service", contacts="count")
    canonical = map_upload(header, rows, mapping)
    assert b"04001" in canonical
    assert len(read_upload(canonical)[1]) == 1
    with pytest.raises(ValueError, match="different"):
        map_upload(header, rows, {**mapping, "contacts": "county"})


@pytest.mark.parametrize("raw", [
    b"a,a\n1,2", b"a,b\n1", b"a\n", b"a\n\x00", b"\xff", b',b\n1,2',
])
def test_bad_file_previews_block(raw):
    with pytest.raises(ValueError):
        read_upload(raw)


def test_multiyear_context_never_becomes_one_month():
    raw, context, study = inputs()
    for row in context:
        row.pop("observation_month")
        row.update(period_start="2020-01", period_end="2024-12")
    with pytest.raises(ValueError, match="rationale"):
        compare_contacts(raw, context, study)
    result = compare_contacts(raw, context, replace(study, period_rationale="Context only"))
    assert result["observation_months"] == []
    assert result["observation_periods"] == [{"start": "2020-01", "end": "2024-12"}]
    context[0]["period_start"] = "2026-01"
    with pytest.raises(ValueError, match="start"):
        compare_contacts(raw, context, study)


def test_downloads_and_hashes_match_results():
    raw, context, study = inputs()
    result = compare_contacts(raw, context, study)
    metadata = dict(synthetic_context=True, measure="Synthetic", period_label="2025-01",
                    population_label="Invented", activity_origin="synthetic bundled example")
    downloads = package(result, study, metadata, raw, {}, "Example")
    receipt = json.loads(downloads["receipt.json"])
    assert receipt["result_csv_sha256"] == hashlib.sha256(downloads["results.csv"]).hexdigest()
    assert receipt["original_input_sha256"] == hashlib.sha256(raw).hexdigest()
    report = json.loads(downloads["join-report.json"])
    assert report["counties_without_records"] == ["04013"]
    assert report["counts"]["flagged"] == 2
    assert "SYNTHETIC" in downloads["brief.md"].decode()
    assert b"'=HYPERLINK" in export_csv([{"program": "=HYPERLINK(x)"}])


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def test_guided_example_and_optional_highlights():
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Outreach workbench").run()
    assert not app.exception
    assert not app.number_input
    assert not app.get("file_uploader")
    click(app, "Try an example")
    assert not app.number_input
    table = next(frame.value for frame in app.dataframe if "County" in frame.value)
    assert table["Contacts per 1,000 residents"].tolist()[:3] == [1, 4, 0]
    assert "Meets my criteria" not in table
    assert any(item.label == "Download comparison report" for item in app.get("download_button"))
    app.toggle(key="wb_highlight").set_value(True).run()
    app.number_input(key="wb_activity").set_value(0.5).run()
    table = next(frame.value for frame in app.dataframe if "County" in frame.value)
    assert (table["Meets my criteria"] == "Yes").sum() == 1
    app.toggle(key="wb_highlight").set_value(False).run()
    assert not app.number_input
    click(app, "Start over")
    assert "wb_payload" not in app.session_state
    assert not app.dataframe
    click(app, "Use my spreadsheet")
    assert len(app.get("file_uploader")) == 1
    assert not any("Bundled synthetic example" == item.label for item in app.radio)


def test_exact_county_name_mapping_and_ambiguous_names():
    from healthcare_di.workbench_view import canonical_counties

    header = ["County", "Month", "Program", "Contacts"]
    mapping = dict(zip(("county_fips", "reporting_month", "program", "contacts"),
                       header, strict=True))
    names = {"04001": "Apache", "04003": "Cochise"}
    data = canonical_counties(header, [[" Apache County ", "2025-01", "Demo outreach", "10"]],
                              mapping, names)
    assert b"04001" in data
    with pytest.raises(ValueError, match="not recognized"):
        canonical_counties(header, [["Apach", "2025-01", "Demo outreach", "10"]],
                           mapping, names)


def test_disabled_highlighting_not_exported():
    raw, context, study = inputs()
    result = compare_contacts(raw, context, study)
    metadata = dict(synthetic_context=True, measure="Synthetic", period_label="2025-01",
                    population_label="Invented", activity_origin="synthetic bundled example",
                    highlight_enabled=False)
    downloads = package(result, study, metadata, raw, {}, "Example")
    receipt = json.loads(downloads["receipt.json"])
    assert receipt["study"]["highlight_enabled"] is False
    assert receipt["study"]["need_threshold"] is None
    assert "flagged" not in receipt["join_counts"]
    assert "investigate" not in downloads["results.csv"].decode().splitlines()[0]
    assert "No counties are flagged" in downloads["brief.md"].decode()


def test_upload_journey_recognizes_names_and_requires_date_acknowledgement(monkeypatch):
    from io import BytesIO

    import streamlit as st

    content = (
        b"County,Month,Program,Contacts\n"
        b"Apache,2026-09,Outreach,10\n"
        b"Coconino,2026-09,Outreach,0\n"
    )
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: BytesIO(content))
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Outreach workbench").run()
    click(app, "Use my spreadsheet")
    assert next(item for item in app.button if item.label == "Show my comparison").disabled
    app.checkbox[0].check().run()
    click(app, "Show my comparison")
    table = next(frame.value for frame in app.dataframe if "Record status" in frame.value)
    assert len(table) == 15
    assert table.loc[table["County"] == "Apache", "Contacts"].iloc[0] == 10
    assert table.loc[table["County"] == "Coconino", "Record status"].iloc[0] == "Reported zero"
    assert (table["Record status"] == "No record supplied").sum() == 13
    assert not app.number_input


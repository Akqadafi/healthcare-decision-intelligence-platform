"""Verify the Step 1 design examples against existing county comparison logic."""

import csv
import json
from pathlib import Path

from healthcare_di.workbench import Study, ValidationError, compare_contacts, parse_contacts

ROOT = Path(__file__).resolve().parents[1] / "examples/workbench-pilot"


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    config = json.loads((ROOT / "study_SYNTHETIC.json").read_text(encoding="utf-8"))
    study = Study(
        tuple(config["counties"]),
        config["month"],
        config["program"],
        config["need_threshold"],
        config["activity_threshold"],
    )
    result = compare_contacts(
        (ROOT / config["upload_file"]).read_bytes(),
        rows(ROOT / config["context_file"]),
        study,
    )
    assert result["counts"] == config["expected_counts"], "Join accounting differs"
    expected = rows(ROOT / "expected_results.csv")
    assert len(result["results"]) == len(expected)
    for actual, wanted in zip(result["results"], expected, strict=True):
        assert actual["county_fips"] == wanted["county_fips"]
        for field in ("contacts", "need_percent", "resident_population", "contacts_per_1000"):
            number = float(wanted[field]) if wanted[field] else None
            assert actual[field] == number, (actual["county_fips"], field)
        flag = {"true": True, "false": False, "": None}[wanted["investigate"]]
        assert actual["investigate"] is flag
        assert actual["reasons"] == ([wanted["reasons"]] if wanted["reasons"] else [])

    failures = json.loads((ROOT / "expected_validation.json").read_text(encoding="utf-8"))
    for filename, wanted in failures.items():
        try:
            parse_contacts((ROOT / filename).read_bytes(), study)
        except ValidationError as error:
            assert any(
                issue.row == wanted["row"]
                and issue.field == wanted["field"]
                and wanted["message_contains"] in issue.message
                for issue in error.issues
            ), filename
        else:
            raise AssertionError(f"Invalid example accepted: {filename}")
    print("PASS: four county results, join accounting, and five blocked upload examples.")
    print("Tract and service-site templates are design drafts, not supported upload features.")


if __name__ == "__main__":
    main()

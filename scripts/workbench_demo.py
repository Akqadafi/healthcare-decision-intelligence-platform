"""Print the synthetic pilot comparison without starting a web app or contacting AWS."""

import csv
import json
from pathlib import Path

from healthcare_di.workbench import Study, compare_contacts


def main():
    root = Path(__file__).resolve().parents[1] / "examples/workbench-pilot"
    with (root / "context_SYNTHETIC.csv").open(encoding="utf-8", newline="") as handle:
        context = list(csv.DictReader(handle))
    study = Study(tuple(row["county_fips"] for row in context), "2025-01", "Demo outreach")
    result = compare_contacts((root / "outreach_SYNTHETIC.csv").read_bytes(), context, study)
    print(json.dumps({"synthetic": True, **result}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

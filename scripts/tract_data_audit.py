"""Acquire public tract sources and audit their join; no model fitting.

Run from the repository root. Cached raw files are reused and hashed.
Use a new --raw directory for a deliberate source refresh.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData"
TABLES = {"B01003": [1], "B19013": [1], "B17001": [1, 2], "B08201": [1, 2]}
MEASURES = ["diabetes", "mhlth", "access2"]


def acquire(raw, name, url, params=None):
    path = raw / name
    receipt = raw / f"{name}.receipt.json"
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".part")
        with requests.get(url, params=params, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for block in response.iter_content(1024 * 1024):
                    handle.write(block)
            metadata = {
                "url": response.url,
                "retrieved_utc": datetime.now(UTC).isoformat(),
                "last_modified": response.headers.get("Last-Modified"),
            }
        temporary.replace(path)
        receipt.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if not receipt.exists():
        raise ValueError(f"Missing acquisition receipt: {receipt}")
    metadata = json.loads(receipt.read_text(encoding="utf-8"))
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    metadata.update(file=name, sha256=digest)
    return path, metadata


def check_ids(frame, column):
    if not frame[column].str.fullmatch(r"04\d{9}").all():
        raise ValueError(f"Invalid Arizona tract identifier in {column}")
    if frame[column].duplicated().any():
        raise ValueError(f"Duplicate tract identifier in {column}")


def read_acs(path, table):
    parts = []
    for chunk in pd.read_csv(path, sep="|", dtype=str, keep_default_na=False, chunksize=25000):
        parts.append(chunk.loc[chunk.GEO_ID.str.fullmatch(r"1400000US04\d{9}")])
    frame = pd.concat(parts, ignore_index=True)
    frame["tractfips"] = frame.GEO_ID.str.removeprefix("1400000US")
    check_ids(frame, "tractfips")
    columns = [f"{table}_{kind}{index:03d}" for index in TABLES[table] for kind in "EM"]
    return frame[["tractfips", *columns]]


def audit(raw, out):
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    sources = []

    def fetch(name, url, params=None):
        path, receipt = acquire(raw, name, url, params)
        sources.append(receipt)
        return path

    fetch("places_metadata.json", "https://data.cdc.gov/api/views/yjkw-uj5s.json")
    places_path = fetch("places_az.json", "https://data.cdc.gov/resource/yjkw-uj5s.json", {
        "$where": "stateabbr='AZ'", "$limit": 10000, "$order": "tractfips",
    })
    places = pd.DataFrame(json.loads(places_path.read_text(encoding="utf-8")))
    if len(places) == 10000 or places.empty:
        raise ValueError("Empty or possibly truncated PLACES response")
    check_ids(places, "tractfips")
    acs = None
    definitions = {}
    for table in TABLES:
        metadata = fetch(f"{table}_metadata.json",
                         f"https://api.census.gov/data/2023/acs/acs5/groups/{table}.json")
        definitions[table] = json.loads(metadata.read_text(encoding="utf-8"))["variables"]
        path = fetch(f"{table}.dat", f"{BASE}/acsdt5y2023-{table.lower()}.dat")
        frame = read_acs(path, table)
        acs = frame if acs is None else acs.merge(frame, on="tractfips", how="outer",
                                                 validate="one_to_one")
    joined = acs.merge(places, on="tractfips", how="outer", validate="one_to_one", indicator=True)
    joined = joined.sort_values("tractfips").reset_index(drop=True)
    joined["county_fips"] = joined.tractfips.str[:5]
    # Keep source strings (including suppression/status codes) alongside clean numeric values.
    for column in acs.columns.drop("tractfips"):
        numeric = pd.to_numeric(joined[column], errors="coerce")
        joined[f"{column}_numeric"] = numeric.where(numeric >= 0)
    for measure in MEASURES:
        joined[f"{measure}_pct"] = pd.to_numeric(joined[f"{measure}_crudeprev"], errors="coerce")
        if not joined[f"{measure}_pct"].dropna().between(0, 100).all():
            raise ValueError(f"Invalid percentage for {measure}")
    for name, table in [("poverty", "B17001"), ("no_vehicle", "B08201")]:
        denominator = joined[f"{table}_E001_numeric"]
        numerator = joined[f"{table}_E002_numeric"]
        valid = (denominator > 0) & (numerator <= denominator)
        joined[f"{name}_pct"] = (100 * numerator / denominator).where(valid)
    joined["median_household_income"] = joined.B19013_E001_numeric
    features = ["diabetes_pct", "mhlth_pct", "access2_pct", "poverty_pct",
                "no_vehicle_pct", "median_household_income"]
    joined["candidate_complete"] = joined[features].notna().all(axis=1)
    joined["missing_candidates"] = joined[features].isna().apply(
        lambda row: ",".join(row.index[row]), axis=1)
    joined.drop(columns=["geolocation"]).to_csv(out / "tract_join_audit.csv", index=False)
    joined[features].describe().to_csv(out / "candidate_distributions.csv")
    joined[features].corr().to_csv(out / "candidate_correlations.csv")
    joined.groupby(["county_fips", "candidate_complete"]).size().rename("tracts").to_csv(
        out / "county_coverage.csv")
    selected_definitions = {}
    for table, indexes in TABLES.items():
        for index in indexes:
            for kind in "EM":
                code = f"{table}_{index:03d}{kind}"
                selected_definitions[code] = definitions[table][code]
    (out / "acs_variable_definitions.json").write_text(
        json.dumps(selected_definitions, indent=2), encoding="utf-8")
    report = {
        "sources": sources, "acs_period": "2019-2023", "places_release": "2025",
        "acs_tracts": len(acs), "places_tracts": len(places),
        "join_counts": joined._merge.value_counts().to_dict(),
        "candidate_complete_tracts": int(joined.candidate_complete.sum()),
        "candidate_missing_counts": joined[features].isna().sum().to_dict(),
        "status": "Data audit only. Candidate features are not an approved fitted model.",
        "boundary_status": "2023 tract identifiers; polygon boundary audit pending",
        "uncertainty": (
            "Raw ACS MOEs and PLACES 95% intervals retained. Derived ratio MOEs pending."
        ),
    }
    (out / "source_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "sources"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw/tract-study-2026-10-24"))
    parser.add_argument("--out", type=Path, default=Path("docs/evidence/tract-study"))
    args = parser.parse_args()
    audit(args.raw, args.out)

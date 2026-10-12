"""Build the gold community priority mart from live data or bundled snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from healthcare_di.config import GOLD_DIR, PROJECT_ROOT, SNAPSHOT_DIR
from healthcare_di.ingestion import (
    fetch_cdc_places,
    fetch_census_acs,
    fetch_cms_hospitals,
    normalize_cdc,
)
from healthcare_di.quality import assert_quality, quality_frame
from healthcare_di.scoring import build_priority_mart


def load_snapshots() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    places = normalize_cdc(pd.read_csv(SNAPSHOT_DIR / "cdc_places_az_2025.csv", dtype=str))
    hospitals = pd.read_csv(SNAPSHOT_DIR / "cms_hospitals_az_2026.csv")
    census = pd.read_csv(SNAPSHOT_DIR / "census_acs_az_2024.csv", dtype={"county_fips": str})
    return places, hospitals, census


def build(*, live: bool = False, output_dir: Path | None = None) -> pd.DataFrame:
    output_dir = output_dir or (PROJECT_ROOT / "data/live" if live else GOLD_DIR)
    if live and output_dir.resolve() == GOLD_DIR.resolve():
        raise ValueError("Live refresh output must be separate from bundled data/gold.")
    places, hospitals, census = (
        (fetch_cdc_places(), fetch_cms_hospitals(), fetch_census_acs())
        if live
        else load_snapshots()
    )
    mart = build_priority_mart(places, hospitals, census)
    assert_quality(mart)
    output_dir.mkdir(parents=True, exist_ok=True)
    mart_path = output_dir / "mart_community_priority.csv"
    temporary = mart_path.with_suffix(".csv.tmp")
    mart.to_csv(temporary, index=False)
    temporary.replace(mart_path)
    quality_frame(mart).to_csv(output_dir / "data_quality_report.csv", index=False)
    manifest = {
        "built_at_utc": datetime.now(UTC).isoformat(),
        "mode": "live" if live else "snapshot",
        "mart_sha256": hashlib.sha256(mart_path.read_bytes()).hexdigest(),
        "row_count": len(mart),
        "quality_status": "passed",
    }
    (output_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2))
    return mart


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Refresh CDC and CMS APIs")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    output_dir = args.output_dir or (PROJECT_ROOT / "data/live" if args.live else GOLD_DIR)
    mart = build(live=args.live, output_dir=output_dir)
    print(f"Built {len(mart)} county records in {output_dir}")


if __name__ == "__main__":
    main()

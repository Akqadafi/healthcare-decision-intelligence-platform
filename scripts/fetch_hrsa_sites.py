"""Refresh a bounded Arizona HRSA snapshot; never fetched during dashboard visits."""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import requests

SOURCE = ("https://gisportal.hrsa.gov/server/rest/services/HealthCareFacilities/"
          "PrimaryHealthCareFacilities_FS/MapServer/0")
FIELDS = ["SITE_SOURCE_ID", "SITE_NM", "SITE_ADDRESS", "SITE_CITY", "SITE_STATE_ABBR",
          "SITE_ZIP_CD", "SITE_PHONE_NUM", "HCC_STATUS_DESC", "HCC_LOC_DESC", "HCC_TYP_DESC",
          "STATE_COUNTY_FIPS_CD", "COUNTY_NM", "LOC_NAME_DESC"]


def main():
    params = {"where": "SITE_STATE_ABBR = 'AZ'", "outFields": ",".join(FIELDS),
              "returnGeometry": "true", "outSR": 4326, "f": "json"}
    response = requests.get(SOURCE + "/query", params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload or payload.get("exceededTransferLimit"):
        raise ValueError("HRSA query failed or exceeded its transfer limit; do not publish")
    features = payload["features"]
    count_response = requests.get(SOURCE + "/query", params={
        "where": params["where"], "returnCountOnly": "true", "f": "json"}, timeout=60)
    count_response.raise_for_status()
    if len(features) != count_response.json().get("count") or not features:
        raise ValueError("HRSA count changed or response is incomplete; retry refresh")
    root = Path(__file__).resolve().parents[1] / "docs/evidence/hrsa"
    raw = json.dumps(payload, indent=2).encode()
    manifest = {
        "source": SOURCE, "query": params, "retrieved_utc": datetime.now(UTC).isoformat(),
        "source_updated_at": None,
        "date_note": "No dataset update date exposed; retrieval is not a source update date.",
        "rows": len(features), "sha256": hashlib.sha256(raw).hexdigest(),
        "location_types": dict(Counter(f["attributes"]["HCC_LOC_DESC"] for f in features)),
    }
    # Validate before replacing the bundled snapshot.
    from healthcare_di.health_centers import normalize_sites
    normalize_sites(payload)
    root.mkdir(parents=True, exist_ok=True)
    (root / "arizona_sites.json").write_bytes(raw)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

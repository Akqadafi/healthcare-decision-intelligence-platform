"""Validated, county-scoped HRSA location context, separate from tract modeling."""

import hashlib
import json

import pandas as pd

AZ_COUNTIES = {f"04{n:03d}" for n in range(1, 28, 2)} | {"04012"}


def normalize_sites(payload):
    rows = []
    for feature in payload["features"]:
        a = feature["attributes"]
        g = feature.get("geometry") or {}
        rows.append({
            "site_id": a["SITE_SOURCE_ID"], "name": a["SITE_NM"],
            "address": a["SITE_ADDRESS"], "city": a["SITE_CITY"],
            "state": a["SITE_STATE_ABBR"], "zip": a["SITE_ZIP_CD"],
            "phone": a["SITE_PHONE_NUM"], "status": a["HCC_STATUS_DESC"],
            "location_type": a["HCC_LOC_DESC"], "site_type": a["HCC_TYP_DESC"],
            "county_fips": a["STATE_COUNTY_FIPS_CD"], "county": a["COUNTY_NM"],
            "geocoding": a["LOC_NAME_DESC"], "longitude": g.get("x"), "latitude": g.get("y"),
        })
    sites = pd.DataFrame(rows)
    if sites.empty or sites.site_id.isna().any() or sites.site_id.duplicated().any():
        raise ValueError("HRSA snapshot has missing or duplicate site IDs")
    if not sites.state.eq("AZ").all() or not sites.county_fips.isin(AZ_COUNTIES).all():
        raise ValueError("HRSA snapshot contains unsupported geography")
    for col in ["latitude", "longitude"]:
        sites[col] = pd.to_numeric(sites[col], errors="coerce")
    sites["mappable"] = (sites.latitude.between(31.0, 37.1)
                         & sites.longitude.between(-115.0, -109.0))
    return sites


def load_sites(root):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    raw = (root / "arizona_sites.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("HRSA snapshot checksum mismatch")
    sites = normalize_sites(json.loads(raw))
    if len(sites) != manifest["rows"]:
        raise ValueError("HRSA snapshot row count mismatch")
    return sites, manifest


def filter_sites(sites, county_fips, include_other=False):
    mask = sites.county_fips.isin(county_fips) & sites.status.eq("Active")
    mask &= sites.site_type.isin(["Service Delivery Site", "Administrative/Service Delivery Site"])
    if not include_other:
        mask &= sites.location_type.eq("Permanent")
    return sites.loc[mask].sort_values(["name", "site_id"]).copy()

"""Public-source ingestion with deterministic snapshot fallbacks."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests

from healthcare_di.config import (
    CDC_API_URL,
    CDC_COLUMNS,
    CENSUS_PROFILE_URL,
    CMS_API_URL,
)


class IngestionError(RuntimeError):
    """Raised when a public source cannot be retrieved or parsed."""


def _get_json(url: str, params: dict[str, Any], timeout: int = 45) -> Any:
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise IngestionError(f"Unable to retrieve {url}: {exc}") from exc


def fetch_cdc_places(state: str = "AZ") -> pd.DataFrame:
    """Fetch the current CDC PLACES county-level GIS-friendly release."""
    params = {
        "$select": ",".join(CDC_COLUMNS),
        "$where": f"stateabbr='{state.upper()}'",
        "$order": "countyfips",
        "$limit": 5000,
    }
    rows = _get_json(CDC_API_URL, params)
    if not rows:
        raise IngestionError(f"CDC PLACES returned no counties for {state}")

    records: list[dict[str, Any]] = []
    for row in rows:
        location = row.pop("geolocation", {}) or {}
        longitude, latitude = (location.get("coordinates") or [None, None])[:2]
        row["longitude"] = longitude
        row["latitude"] = latitude
        records.append(row)
    return normalize_cdc(pd.DataFrame(records))


def normalize_cdc(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize PLACES API or snapshot columns to the canonical schema."""
    rename = {
        "stateabbr": "state",
        "countyname": "county_name",
        "countyfips": "county_fips",
        "totalpopulation": "population",
        "access2_crudeprev": "uninsured_rate",
        "checkup_crudeprev": "annual_checkup_rate",
        "obesity_crudeprev": "obesity_rate",
        "diabetes_crudeprev": "diabetes_rate",
        "bphigh_crudeprev": "hypertension_rate",
        "phlth_crudeprev": "poor_physical_health_rate",
        "mhlth_crudeprev": "poor_mental_health_rate",
        "foodinsecu_crudeprev": "food_insecurity_rate",
        "lacktrpt_crudeprev": "transportation_barrier_rate",
    }
    normalized = frame.rename(columns=rename).copy()
    numeric = [
        "population",
        "uninsured_rate",
        "annual_checkup_rate",
        "obesity_rate",
        "diabetes_rate",
        "hypertension_rate",
        "poor_physical_health_rate",
        "poor_mental_health_rate",
        "food_insecurity_rate",
        "transportation_barrier_rate",
        "latitude",
        "longitude",
    ]
    for column in numeric:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["county_fips"] = normalized["county_fips"].astype(str).str.zfill(5)
    normalized["county_name"] = normalized["county_name"].str.strip().str.title()
    return normalized


def fetch_cms_hospitals(state: str = "AZ") -> pd.DataFrame:
    """Fetch CMS Hospital General Information and aggregate to county level."""
    params = {
        "offset": 0,
        "limit": 500,
        "conditions[0][property]": "state",
        "conditions[0][value]": state.upper(),
        "conditions[0][operator]": "=",
    }
    payload = _get_json(CMS_API_URL, params, timeout=60)
    rows = payload.get("results", [])
    if not rows:
        raise IngestionError(f"CMS returned no hospitals for {state}")
    return aggregate_cms(pd.DataFrame(rows))


def aggregate_cms(frame: pd.DataFrame) -> pd.DataFrame:
    """Create auditable access/quality measures from hospital-level CMS data."""
    data = frame.copy()
    data["hospital_rating_numeric"] = pd.to_numeric(
        data["hospital_overall_rating"], errors="coerce"
    )
    data["emergency_flag"] = data["emergency_services"].eq("Yes")
    data["birthing_flag"] = data["meets_criteria_for_birthing_friendly_designation"].eq("Y")
    data["county_key"] = (
        data["countyparish"].str.upper().str.replace(" ", "", regex=False).str.strip()
    )
    grouped = data.groupby("county_key", as_index=False).agg(
        hospital_count=("facility_id", "count"),
        rated_hospital_count=("hospital_rating_numeric", "count"),
        average_hospital_rating=("hospital_rating_numeric", "mean"),
        emergency_hospital_count=("emergency_flag", "sum"),
        birthing_friendly_count=("birthing_flag", "sum"),
    )
    grouped["average_hospital_rating"] = grouped["average_hospital_rating"].round(2)
    return grouped


def fetch_census_acs(state_fips: str = "04", api_key: str | None = None) -> pd.DataFrame:
    """Fetch optional ACS income and poverty enrichment (API key required)."""
    key = api_key or os.getenv("CENSUS_API_KEY")
    if not key:
        raise IngestionError("CENSUS_API_KEY is required by the Census API as of 2026")
    params = {
        "get": "NAME,DP03_0062E,DP03_0128PE",
        "for": "county:*",
        "in": f"state:{state_fips}",
        "key": key,
    }
    rows = _get_json(CENSUS_PROFILE_URL, params)
    header, *values = rows
    frame = pd.DataFrame(values, columns=header)
    frame["county_fips"] = frame["state"] + frame["county"]
    frame = frame.rename(
        columns={"DP03_0062E": "median_household_income", "DP03_0128PE": "poverty_rate"}
    )[["county_fips", "median_household_income", "poverty_rate"]]
    frame["median_household_income"] = pd.to_numeric(
        frame["median_household_income"], errors="coerce"
    )
    frame["poverty_rate"] = pd.to_numeric(frame["poverty_rate"], errors="coerce")
    return frame

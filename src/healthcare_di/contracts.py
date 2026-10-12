"""Enforce versioned source contracts before joins and scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from healthcare_di.config import PROJECT_ROOT

ARIZONA_FIPS = {f"04{county:03d}" for county in range(1, 28, 2)} | {"04012"}


def validate_contract(frame: pd.DataFrame, filename: str) -> None:
    contract = yaml.safe_load((PROJECT_ROOT / "data_contracts" / filename).read_text())
    errors = []
    fields = contract["required_columns"]
    missing = sorted(set(fields) - set(frame.columns))
    if missing:
        raise ValueError(f"{contract['dataset']} contract: missing columns {missing}")
    for column, rule in fields.items():
        values = frame[column]
        present = values.notna()
        if not rule.get("nullable", False) and not present.all():
            errors.append(f"{column}: null values")
        if rule["type"] in ("number", "integer"):
            numeric = pd.to_numeric(values, errors="coerce")
            if not np.isfinite(numeric[present]).all():
                errors.append(f"{column}: expected finite numbers")
            if rule["type"] == "integer" and (numeric[present] % 1 != 0).any():
                errors.append(f"{column}: expected integers")
            if "min" in rule and (numeric[present] < rule["min"]).any():
                errors.append(f"{column}: below {rule['min']}")
            if "max" in rule and (numeric[present] > rule["max"]).any():
                errors.append(f"{column}: above {rule['max']}")
        else:
            if not values[present].map(lambda value: isinstance(value, str)).all():
                errors.append(f"{column}: expected strings")
            if not rule.get("allow_empty") and values[present].astype(str).str.strip().eq("").any():
                errors.append(f"{column}: empty strings")
            if (
                "pattern" in rule
                and not values[present].astype(str).str.fullmatch(rule["pattern"]).all()
            ):
                errors.append(f"{column}: invalid format")
    key = contract["primary_key"]
    if frame[key].duplicated().any():
        errors.append(f"{key}: duplicate keys")
    if contract.get("expected_arizona_counties"):
        if set(frame[key]) != ARIZONA_FIPS or len(frame) != 15:
            errors.append("expected exactly the 15 Arizona county FIPS")
    if errors:
        raise ValueError(f"{contract['dataset']} contract: " + "; ".join(errors))


def validate_scoring_inputs(places, hospitals, census) -> None:
    if census is None:
        raise ValueError("Census input is required for income and poverty scoring.")
    validate_contract(places, "cdc_places_contract.yml")
    validate_contract(census, "census_acs_contract.yml")
    validate_contract(hospitals, "cms_county_contract.yml")
    expected_keys = set(places["county_name"].str.upper().str.replace(" ", "", regex=False))
    if not set(hospitals["county_key"]).issubset(expected_keys):
        raise ValueError("Hospital county keys must match Arizona county names.")
    for column in ["median_household_income", "poverty_rate"]:
        if census[column].isna().all():
            raise ValueError(
                f"Census {column} is entirely missing; median imputation is undefined."
            )
    for column in ["rated_hospital_count", "emergency_hospital_count", "birthing_friendly_count"]:
        if (hospitals[column] > hospitals["hospital_count"]).any():
            raise ValueError(f"{column} cannot exceed hospital_count.")

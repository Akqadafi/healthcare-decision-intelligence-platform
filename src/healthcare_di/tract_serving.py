"""Read saved tract models without importing or fitting machine-learning estimators."""

import hashlib
import json
from pathlib import Path

import pandas as pd

MEASURES = {
    "diabetes_pct": "Diabetes (%)",
    "mhlth_pct": "Frequent mental distress (%)",
    "access2_pct": "Uninsured adults 18–64 (%)",
    "poverty_pct": "People below poverty (%)",
    "no_vehicle_pct": "Households without a vehicle (%)",
}


def load_study(root: Path):
    manifest = json.loads((root / "models/model_manifest.json").read_text())
    for name in ["tract_profiles.csv", "all_assignments.csv", "model_comparison.csv",
                 "perturbations.csv"]:
        actual = hashlib.sha256((root / "models" / name).read_bytes()).hexdigest()
        if actual != manifest["output_sha256"][name]:
            raise ValueError(f"Saved study checksum mismatch: {name}")
    data = pd.read_csv(root / "models/tract_profiles.csv",
                       dtype={"tractfips": str, "county_fips": str})
    labels = pd.read_csv(root / "models/all_assignments.csv", dtype={"tractfips": str})
    if data.tractfips.duplicated().any() or labels.tractfips.duplicated().any():
        raise ValueError("Duplicate tract identifiers in saved study")
    if set(labels.tractfips) != set(data.loc[data.eligible, "tractfips"]):
        raise ValueError("Assignments do not match eligible tracts")
    data = data.merge(labels, on="tractfips", how="left", validate="one_to_one")
    names = data.dropna(subset=["countyname"]).set_index("county_fips").countyname.to_dict()
    data["countyname"] = data.county_fips.map(names).fillna(data.county_fips)
    return (data, pd.read_csv(root / "models/model_comparison.csv"),
            pd.read_csv(root / "models/perturbations.csv", dtype={"variant": str}),
            manifest,
            json.loads((root / "tract_boundaries.geojson").read_text()))


def model_view(data, model):
    if model not in data or not model.startswith(("kmeans_k", "ward_k")):
        raise ValueError("Unknown saved model")
    result = data.copy()
    result["profile"] = result[model].map(
        lambda value: "Excluded" if pd.isna(value) else f"Group {int(value) + 1}")
    return result


def filter_view(data, counties, group, measure, limits, include_missing, include_excluded):
    mask = data.countyname.isin(counties)
    if group != "All groups":
        mask &= data.profile.eq(group)
    if not include_excluded:
        mask &= data.eligible
    values = data[measure]
    mask &= values.between(*limits) | (include_missing & values.isna())
    return data.loc[mask].copy()

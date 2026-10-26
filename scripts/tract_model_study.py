"""Reproduce the tract model comparison from audited local inputs; no network calls."""

import hashlib
import importlib.metadata
import json
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from healthcare_di.tract_models import FEATURES, SEED, cohort, compare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = Path("docs/evidence/tract-study")
    output = source / "models"
    output.mkdir(exist_ok=True)
    boundaries = pd.read_csv(source / "boundary_join.csv", dtype={"tractfips": str})
    data = pd.read_csv(source / "tract_join_audit.csv",
                       dtype={"tractfips": str, "county_fips": str})
    if (not boundaries._merge.eq("both").all() or boundaries.tractfips.duplicated().any()
            or set(boundaries.tractfips) != set(data.tractfips)):
        raise ValueError("Boundary coverage must match all data before fitting")
    data = cohort(data)
    eligible = data.loc[data.eligible].copy().reset_index(drop=True)
    with threadpool_limits(limits=1):
        metrics, perturbations, assignments = compare(eligible)
    metrics.to_csv(output / "model_comparison.csv", index=False)
    perturbations.to_csv(output / "perturbations.csv", index=False)
    passed = metrics.loc[metrics.passes_project_rules]
    candidates = passed if len(passed) else metrics
    selected = candidates.sort_values(["silhouette", "model"], ascending=[False, True]).iloc[0]
    model_id = selected.model
    status = "passes_project_heuristics" if len(passed) else "exploratory_only_no_candidate_passed"
    label_table = eligible[["tractfips"]].copy()
    for name, labels in assignments.items():
        label_table[name] = labels
    label_table.to_csv(output / "all_assignments.csv", index=False)
    eligible["profile"] = [f"Group {label + 1}" for label in assignments[model_id]]
    data = data.merge(eligible[["tractfips", "profile"]], on="tractfips", how="left",
                      validate="one_to_one")
    data["profile"] = data.profile.fillna("Excluded")
    data.to_csv(output / "tract_profiles.csv", index=False)
    eligible.groupby("profile")[FEATURES].agg(["mean", "median", "min", "max"]).to_csv(
        output / "profile_statistics.csv")
    eligible.groupby("profile").size().rename("tracts").to_csv(output / "profile_sizes.csv")
    data.groupby(["county_fips", "eligible"]).agg(
        tracts=("tractfips", "size"), population=("B01003_E001_numeric", "sum")
    ).to_csv(output / "cohort_coverage.csv")
    profile_by_county = pd.crosstab(data.county_fips, data.profile)
    profile_by_county.to_csv(output / "profiles_by_county.csv")
    manifest = {
        "study_version": "az-tract-v1", "seed": SEED, "features": FEATURES,
        "eligible_tracts": len(eligible), "excluded_tracts": len(data) - len(eligible),
        "display_model": model_id, "status": status,
        "selection": "Highest silhouette among passing candidates, otherwise exploratory best",
        "settings": {"k": [2, 3, 4, 5, 6], "subsamples": 20, "fraction": 0.8,
                     "kmeans_n_init": 30, "scaler": "StandardScaler", "thread_limit": 1},
        "versions": {name: importlib.metadata.version(name) for name in
                     ("numpy", "pandas", "scipy", "scikit-learn", "threadpoolctl", "pyshp")},
        "input_sha256": {str(path): digest(path) for path in [
            source / "tract_join_audit.csv", source / "boundary_join.csv",
            source / "boundary_audit.json", source / "source_audit.json",
            Path("src/healthcare_di/tract_models.py"), Path(__file__),
            Path("docs/TRACT_MODEL_DECISIONS.md")]},
        "limitations": ["No causal or individual health inference",
                        "No propagation of survey/model uncertainty through clustering",
                        "Derived-rate margins of error omitted; source components retained",
                        "PLACES modeled estimates include ACS inputs; crude rates reflect age",
                        "ARI perturbations are not predictive validation",
                        "Group numbers have no rank; filters must not refit saved models"],
    }
    manifest["output_sha256"] = {p.name: digest(p) for p in sorted(output.glob("*.csv"))}
    (output / "model_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in
                      ("eligible_tracts", "excluded_tracts", "display_model", "status")}, indent=2))


if __name__ == "__main__":
    main()

"""Descriptive tract clustering with explicit cohort and perturbation checks."""

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import RobustScaler, StandardScaler

FEATURES = ["diabetes_pct", "mhlth_pct", "access2_pct", "poverty_pct", "no_vehicle_pct"]
SEED = 20261024


def cohort(data):
    """Keep all input rows; annotate exclusion reasons rather than silently dropping."""
    result = data.copy()
    if result.tractfips.isna().any() or result.tractfips.duplicated().any():
        raise ValueError("Missing or duplicate tract identifiers")
    if not result.tractfips.str.fullmatch(r"04\d{9}").all():
        raise ValueError("Expected Arizona tract identifiers as strings")
    for feature in FEATURES:
        present = result[feature].dropna()
        if not np.isfinite(present).all() or not present.between(0, 100).all():
            raise ValueError(f"Invalid percentage: {feature}")
    result["exclusion_reason"] = result[FEATURES].isna().apply(
        lambda row: ",".join(row.index[row]), axis=1)
    invalid_pop = result.B01003_E001_numeric.isna() | (result.B01003_E001_numeric <= 0)
    result.loc[invalid_pop, "exclusion_reason"] += ",nonpositive_or_missing_population"
    result["exclusion_reason"] = result.exclusion_reason.str.strip(",")
    result["eligible"] = result.exclusion_reason.eq("")
    return result.sort_values("tractfips").reset_index(drop=True)


def fit(values, method, k, seed=SEED, robust=False):
    """Every call fits fresh preprocessing, including all sensitivity/resampling fits."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all() or not 2 <= k < len(values):
        raise ValueError("Need finite 2D features and 2 <= k < sample size")
    scaler = RobustScaler() if robust else StandardScaler()
    scaled = scaler.fit_transform(values)
    if method == "kmeans":
        model = KMeans(n_clusters=k, n_init=30, random_state=seed)
    elif method == "ward":
        model = AgglomerativeClustering(n_clusters=k, linkage="ward")
    else:
        raise ValueError("Unknown clustering method")
    labels = model.fit_predict(scaled)
    if len(np.unique(labels)) != k:
        raise ValueError("Degenerate clustering")
    return labels, scaled


def passes_rules(row):
    return bool(row["silhouette"] >= 0.25 and row["minimum_share"] >= 0.05
                and row["subsample_ari_median"] >= 0.80
                and row["subsample_ari_p10"] >= 0.65
                and row["omit_feature_ari_min"] >= 0.60)


def compare(data, repeats=20):
    """Compare full fits to refits on common rows; ARI is independent of label names."""
    if repeats < 2:
        raise ValueError("At least two subsamples are required")
    values = data[FEATURES].to_numpy()
    if len(data) < 30:
        raise ValueError("Study comparison requires at least 30 eligible tracts")
    summaries, perturbations, assignments = [], [], {}
    for method in ("kmeans", "ward"):
        for k in range(2, 7):
            model_id = f"{method}_k{k}"
            labels, scaled = fit(values, method, k)
            assignments[model_id] = labels
            rng = np.random.default_rng(SEED)
            scores, omissions = [], []

            def record(kind, name, score, n, model_id=model_id):
                perturbations.append({"model": model_id, "kind": kind, "variant": str(name),
                                      "ari": float(score), "comparison_tracts": int(n)})

            for iteration in range(repeats):
                rows = np.sort(rng.choice(len(data), int(0.8 * len(data)), replace=False))
                perturbed, _ = fit(values[rows], method, k, seed=SEED + iteration)
                score = adjusted_rand_score(labels[rows], perturbed)
                scores.append(score)
                record("subsample", iteration, score, len(rows))
            for omitted in FEATURES:
                remaining = [f for f in FEATURES if f != omitted]
                other, _ = fit(data[remaining], method, k)
                score = adjusted_rand_score(labels, other)
                omissions.append(score)
                record("omit_feature", omitted, score, len(data))
            robust_labels, _ = fit(values, method, k, robust=True)
            record("scaling", "robust", adjusted_rand_score(labels, robust_labels), len(data))
            common = data.median_household_income.notna().to_numpy()
            if common.sum() > k:
                base_common, _ = fit(values[common], method, k)
                alternate = [f if f != "poverty_pct" else "median_household_income"
                             for f in FEATURES]
                alternate_labels, _ = fit(data.loc[common, alternate], method, k)
                record("replace_poverty", "income_on_common_rows",
                       adjusted_rand_score(base_common, alternate_labels), common.sum())
            for county in sorted(data.county_fips.unique()):
                rows = (data.county_fips != county).to_numpy()
                other, _ = fit(values[rows], method, k)
                record("omit_county", county, adjusted_rand_score(labels[rows], other), rows.sum())
            if method == "kmeans":
                for seed in range(SEED + 1, SEED + 6):
                    other, _ = fit(values, method, k, seed=seed)
                    record("initialization", seed, adjusted_rand_score(labels, other), len(data))
            sizes = np.bincount(labels, minlength=k)
            row = {"model": model_id, "method": method, "k": k,
                   "silhouette": float(silhouette_score(scaled, labels)),
                   "minimum_share": float(sizes.min() / len(data)),
                   "subsample_ari_median": float(np.median(scores)),
                   "subsample_ari_p10": float(np.quantile(scores, 0.1)),
                   "omit_feature_ari_min": float(min(omissions))}
            row["passes_project_rules"] = passes_rules(row)
            summaries.append(row)
            print(f"Finished {model_id}", flush=True)
    return pd.DataFrame(summaries), pd.DataFrame(perturbations), assignments

"""Create a standalone interactive analysis report from saved model outputs."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

from healthcare_di.tract_models import FEATURES


def main():
    root = Path("docs/evidence/tract-study")
    output = root / "models"
    manifest = json.loads((output / "model_manifest.json").read_text())
    metrics = pd.read_csv(output / "model_comparison.csv")
    checks = pd.read_csv(output / "perturbations.csv", dtype={"variant": str})
    data = pd.read_csv(output / "tract_profiles.csv", dtype={"tractfips": str})
    selected = manifest["display_model"]
    colors = {"Group 1": "#0072B2", "Group 2": "#D55E00", "Excluded": "#b8b8b8"}
    metrics["label"] = metrics.model.where(metrics.model.isin([selected, "ward_k2"]), "")
    figures = [px.scatter(
        metrics, x="subsample_ari_median", y="silhouette", color="method", text="label",
        hover_data=["model", "minimum_share", "omit_feature_ari_min", "passes_project_rules"],
        title="All ten candidates: separation and subsample stability",
        labels={"subsample_ari_median": "Median subsample ARI (higher is more agreement)"},
    )]
    figures[0].update_traces(textposition="top center")
    figures.append(px.box(
        checks.loc[checks.model == selected], x="kind", y="ari", points="all",
        hover_data=["variant", "comparison_tracts"],
        title=f"Sensitivity of {selected}: different checks answer different questions",
    ))
    medians = data.loc[data.eligible].groupby("profile")[FEATURES].median().reset_index()
    figures.append(px.bar(
        medians.melt(id_vars="profile", var_name="measure", value_name="percent"),
        x="measure", y="percent", color="profile", barmode="group",
        color_discrete_map=colors,
        title="Group medians in original units (population universes differ)",
    ))
    geometry = json.loads((root / "tract_boundaries.geojson").read_text())
    figures.append(px.choropleth_map(
        data, geojson=geometry, locations="tractfips", featureidkey="id", color="profile",
        hover_data=[*FEATURES, "exclusion_reason"],
        center={"lat": 34.3, "lon": -111.8}, zoom=5, map_style="white-bg",
        opacity=0.7, title="Arizona tract assignments, including excluded tracts",
        color_discrete_map=colors,
    ))
    chunks = []
    for index, figure in enumerate(figures):
        figure.update_layout(template="plotly_white", height=650,
                             margin={"t": 85, "b": 100, "l": 70, "r": 35})
        chunks.append(pio.to_html(figure, full_html=False,
                                  include_plotlyjs=True if index == 0 else False,
                                  div_id=f"tract-study-{index}"))
    status_text = ("The display candidate passed the study's prespecified checks"
                   if manifest["status"] == "passes_project_heuristics" else
                   "No candidate passed all study checks; this is an exploratory example")
    heading = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Arizona tract study</title>"
        "<style>body{font:17px system-ui;max-width:1200px;margin:32px auto;padding:20px}"
        "p{line-height:1.6}.note{padding:16px;background:#fff3cd}</style></head><body>"
        "<h1>Arizona tract clustering study</h1>"
        f"<p>Study az-tract-v1. Display candidate: <b>{selected}</b>. "
        f"Eligible tracts: {manifest['eligible_tracts']}; "
        f"excluded: {manifest['excluded_tracts']}.</p>"
        f"<p class='note'>{status_text}. Group numbers do not rank communities. "
        "This is descriptive analysis of modeled health estimates and ACS survey estimates, "
        "not a clinical or funding recommendation. Charts use saved fits; filtering legends "
        "does not retrain a model.</p>"
        "<p>ACS 2019–2023; PLACES 2025 release. The sampling checks do not propagate "
        "source uncertainty. Derived-rate margins of error are omitted. The map uses "
        "generalized 2023 boundaries and a blank background without external map tiles.</p>"
    )
    (output / "analysis.html").write_text(heading + "".join(chunks) + "</body></html>",
                                          encoding="utf-8")
    print(output / "analysis.html")


if __name__ == "__main__":
    main()

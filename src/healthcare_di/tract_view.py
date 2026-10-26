"""Interactive saved-model exploration inside the original Streamlit dashboard."""

import hashlib
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from healthcare_di.config import PROJECT_ROOT
from healthcare_di.tract_serving import MEASURES, filter_view, load_study, model_view

CONTROL_HELP = {
    "method": "K-means groups similar standardized profiles around centers. Ward merges similar "
              "profiles step by step. This switches saved assignments; it does not train a model.",
    "k": "Drag to choose a saved model with 2–6 groups. More groups means a finer split, "
         "not necessarily a better model. Check the stability warning after changing this.",
    "counties": "Choose one or more counties. Remove a county with its ×, or clear all and type "
                "a county name. An empty selection shows no tracts. Statewide fits stay unchanged.",
    "group": "Show all groups, one group, or tracts excluded from fitting. Group numbers are "
             "labels, not risk ranks, and can mean different things in different models.",
    "measure": "Choose the percentage used for the range filter, summary median, and map hover. "
               "Map colors still identify community groups. This does not change model features.",
    "range": "Move either handle to keep estimates between the two percentages, including both "
             "endpoints. For example, 20–100 with Diabetes shows estimates of at least 20%. "
             "The range stays in place when you change measures.",
    "missing": "Keep tracts with no estimate for the selected measure, even outside a numeric "
               "range. Uncheck this for a view containing only known estimates in the range.",
    "excluded": "Keep tracts omitted from model fitting because of incomplete features or "
                "nonpositive/missing population. They appear gray and still obey other filters. "
                "This does not put them back into the model.",
}


def remember(name):
    st.session_state["tract_controls"][name] = st.session_state[f"_tract_{name}"]


def render():
    root = PROJECT_ROOT / "docs/evidence/tract-study"
    try:
        data, metrics, checks, manifest, geometry = load_study(root)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"The saved tract study is unavailable: {exc}")
        return
    defaults = {"method": "K-means", "k": 2, "counties": sorted(data.countyname.unique()),
                "group": "All groups", "measure": "diabetes_pct", "range": (0.0, 100.0),
                "missing": True, "excluded": True}
    saved = st.session_state.setdefault("tract_controls", defaults.copy())
    with st.sidebar:
        st.subheader("Tract study controls")
        st.caption("Changes update the results automatically. Hover over a ? for control help.")
        if st.button("Reset tract controls", help="Restore two-group K-means, all counties and "
                     "groups, Diabetes, range 0–100, and both inclusion options."):
            saved.clear()
            saved.update(defaults)
        for name, value in saved.items():
            st.session_state[f"_tract_{name}"] = value

        def widget(name):
            return {"key": f"_tract_{name}", "on_change": remember, "args": (name,),
                    "help": CONTROL_HELP[name]}

        method = st.selectbox("Clustering method", ["K-means", "Ward hierarchical"],
                              **widget("method"))
        k = st.select_slider("Number of groups", options=[2, 3, 4, 5, 6], **widget("k"))
        counties = st.multiselect("Counties", defaults["counties"], **widget("counties"))
        groups = ["All groups", *[f"Group {n}" for n in range(1, k + 1)], "Excluded"]
        if saved["group"] not in groups:
            saved["group"] = "All groups"
            st.session_state["_tract_group"] = "All groups"
        group = st.selectbox("Community group", groups, **widget("group"))
        measure = st.selectbox("Measure", list(MEASURES), format_func=MEASURES.get,
                               **widget("measure"))
        limits = st.slider("Measure range (%)", 0.0, 100.0, step=0.5, **widget("range"))
        missing = st.checkbox("Include missing measure values", **widget("missing"))
        excluded = st.checkbox("Include excluded tracts", **widget("excluded"))
        st.caption("These controls select saved results. "
                   "They do not refit models or change inputs.")
    model = f"{'kmeans' if method == 'K-means' else 'ward'}_k{k}"
    full = model_view(data, model)
    visible = filter_view(full, counties, group, measure, limits, missing, excluded)
    selected = metrics.loc[metrics.model.eq(model)].iloc[0]
    st.header("Explore census tracts")
    st.write("Compare community profiles, inspect estimates, and test how saved model choices "
             "affect grouping across Arizona.")
    st.caption("ACS 2019–2023 · CDC PLACES 2025 release · 2023 tract boundaries · "
               f"Study {manifest['study_version']}")
    with st.expander("How to use the controls", expanded=True):
        st.markdown(
            "1. **Choose an area.** In Counties, clear the selections and choose a county "
            "such as Apache. The map, table, comparison choices, and download update together.\n"
            "2. **Choose what to inspect.** Select a Measure, then move the two Measure range "
            "handles. For a diabetes estimate of at least 20%, choose Diabetes and set 20–100. "
            "Uncheck Include missing measure values if you want only known estimates.\n"
            "3. **Explore groupings.** Start with K-means and two groups. Change Clustering method "
            "or Number of groups to compare saved alternatives; review any warning in Stability "
            "& methods. Community group filters to one profile. Map colors show groups, "
            "not the selected measure.\n"
            "4. **Compare and save.** Below the map, choose First tract and Comparison tract. "
            "Read their estimates and uncertainty, then use Downloads & help to save the "
            "filtered CSV and its study receipt.\n"
            "5. **Recover or start over.** No matches? Select a county, widen the range, or click "
            "Reset tract controls. Your choices persist when you leave this page and return."
        )
        st.caption("Missing means no estimate for the selected measure. Excluded means the tract "
                   "was not fitted into a group; it may still have some estimates. Both inclusion "
                   "options work together with the other filters. Statewide profile medians stay "
                   "fixed when you filter. Collapse this panel when you are ready to explore.")
    st.info("County, group, and measure controls filter the view. Method and group count switch "
            "between ten previously fitted statewide models. Group numbers have no rank and "
            "are not equivalent across models. No model is retrained here.")
    if selected.passes_project_rules:
        st.success("This model passed the study's prespecified separation and stability checks.")
    else:
        st.warning("Exploratory comparison: this model did not pass all study checks. "
                   "Use Stability & methods to see which checks were weak.")
    a, b, c = st.columns(3)
    a.metric("Tracts shown", f"{len(visible):,}")
    b.metric("Excluded tracts shown", int((~visible.eligible).sum()))
    median = visible[measure].median()
    c.metric("Median selected measure", "Unavailable" if pd.isna(median) else f"{median:.2f}%")
    c.caption("Median across visible tracts, not population-weighted.")
    explore, stability, downloads = st.tabs(["Map & tract details", "Stability & methods",
                                            "Downloads & help"])
    with explore:
        if visible.empty:
            st.warning("No tracts match these controls. Broaden the range, select a county, "
                       "or use Reset tract controls.")
        else:
            colors = dict(zip([f"Group {n}" for n in range(1, 7)],
                              ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"],
                              strict=True))
            colors["Excluded"] = "#b8b8b8"
            figure = px.choropleth_map(
                visible, geojson=geometry, locations="tractfips", featureidkey="id",
                color="profile", color_discrete_map=colors, map_style="white-bg",
                center={"lat": 34.3, "lon": -111.8}, zoom=5, opacity=0.7,
                hover_name="tractfips", hover_data=["countyname", measure, "exclusion_reason"],
                labels={**MEASURES, "profile": "Community group", "countyname": "County"})
            figure.update_layout(height=550, margin={"l": 0, "r": 0, "t": 10, "b": 0})
            st.plotly_chart(figure, width="stretch")
            st.caption("Gray = excluded from modeling. Zoom and pan to inspect. "
                       "Boundaries are generalized and are unsuitable for distance calculations.")
            columns = ["tractfips", "countyname", "profile", *MEASURES, "exclusion_reason"]
            st.dataframe(visible[columns].rename(columns=MEASURES), hide_index=True,
                         width="stretch")
            options = visible.tractfips.tolist()
            left, right = st.columns(2)
            first = left.selectbox("First tract", options, key="tract_first",
                                   help="Choose a tract from the current filtered results. "
                                        "Its estimates appear in the comparison table below.")
            second = right.selectbox("Comparison tract", options, index=min(1, len(options) - 1),
                                      key="tract_second", help="Choose a second visible tract. "
                                      "Compare estimates and intervals, not just group labels. "
                                      "Choosing the same tract twice shows one column.")
            details = visible.set_index("tractfips").loc[list(dict.fromkeys([first, second]))]
            st.subheader("Compare estimates and uncertainty")
            detail_columns = ["countyname", "profile", *MEASURES, "diabetes_crude95ci",
                              "mhlth_crude95ci", "access2_crude95ci", "B17001_M001",
                              "B17001_M002", "B08201_M001", "B08201_M002", "exclusion_reason"]
            st.dataframe(details[detail_columns].T, width="stretch")
            st.caption("PLACES fields ending in 95ci are modeled 95% intervals. ACS M001/M002 "
                       "are 90% margins of error for denominator/numerator counts, not the "
                       "displayed percentages. Negative source codes indicate unavailable values. "
                       "Derived percentage margins of error are not calculated.")
            st.subheader("Statewide profile medians")
            medians = full.loc[full.eligible].groupby("profile")[list(MEASURES)].median()
            st.dataframe(medians.rename(columns=MEASURES), width="stretch")
            st.caption("These profile medians use the full fitted cohort and stay fixed when "
                       "you filter. Individual tracts can differ from their group median.")
    with stability:
        st.write("Silhouette measures separation. Adjusted Rand index (ARI) measures agreement "
                 "between assignments: 1 means identical grouping, even if labels change. "
                 "Neither is a probability of illness or a measure of predictive accuracy.")
        st.dataframe(metrics, hide_index=True, width="stretch")
        st.dataframe(checks.loc[checks.model.eq(model)], hide_index=True, width="stretch")
        st.markdown("**Study checks:** silhouette ≥0.25; smallest group ≥5%; median subsample "
                    "ARI ≥0.80; tenth-percentile ARI ≥0.65; minimum feature-removal ARI ≥0.60. "
                    "These are project heuristics. Scaling is refitted in each perturbation.")
        st.write("Five equally standardized features: diabetes, mental distress, uninsured adults, "
                 "poverty, and vehicle access. Tracts receive equal weight. PLACES uses modeled "
                 "estimates with ACS inputs; crude rates also reflect age composition. Source "
                 "uncertainty is not propagated through clustering. No causal or allocation "
                 "claims follow from these groups.")
    with downloads:
        csv = visible.to_csv(index=False).encode("utf-8")
        receipt = {"study_version": manifest["study_version"], "model": model,
                   "controls": saved, "rows": len(visible),
                   "csv_sha256": hashlib.sha256(csv).hexdigest(),
                   "model_manifest": manifest}
        st.download_button("Download filtered tract data", csv, f"tracts_{model}.csv", "text/csv",
                           on_click="ignore")
        st.download_button("Download study receipt", json.dumps(receipt, indent=2),
                           "tract_study_receipt.json", "application/json", on_click="ignore")
        st.download_button("Download model comparisons", metrics.to_csv(index=False),
                           "model_comparison.csv", "text/csv", on_click="ignore")
        st.caption("The receipt records the chosen model, filters, study version, and CSV hash. "
                   "Downloads contain public estimates, including source uncertainty fields.")
        for name, label in [("TRACT_DASHBOARD_GUIDE.md", "Dashboard guide"),
                            ("TRACT_DASHBOARD_TUTORIAL.md", "Worked tutorial")]:
            path = PROJECT_ROOT / "docs/user-guide" / name
            if path.exists():
                with st.expander(label):
                    st.markdown(path.read_text(encoding="utf-8"))
                    if name == "TRACT_DASHBOARD_TUTORIAL.md":
                        screenshot = PROJECT_ROOT / "docs/evidence/tract-dashboard/apache.png"
                        if screenshot.exists():
                            st.image(str(screenshot), caption="Verified Apache County walkthrough")

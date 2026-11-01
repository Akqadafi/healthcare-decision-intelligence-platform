"""Interactive saved-model exploration inside the original Streamlit dashboard."""

import hashlib
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from healthcare_di.config import PROJECT_ROOT
from healthcare_di.tract_serving import MEASURES, filter_view, load_study, model_view

CONTROL_HELP = {
    "filter_enabled": "Optional: narrow the map and table by one indicator. Community groups "
                      "still use all five indicators. Turn off to ignore the range and "
                      "missing-value setting.",
    "method": "A grouping method finds tracts with similar patterns across five indicators. "
              "K-means compares tracts with group centers; Ward builds groups by merging "
              "similar ones. Start with the default; you do not need to change this to explore.",
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
    st.session_state.pop("tract_tutorial_step", None)


def tutorial_step(step):
    st.session_state["tract_tutorial_step"] = step
    st.session_state["tract_controls"] = {
        "method": "K-means", "k": 2, "counties": ["Apache"],
        "group": "All groups", "measure": "diabetes_pct",
        "range": (20.0, 100.0) if step >= 2 else (0.0, 100.0),
        "missing": False, "excluded": True, "filter_enabled": step >= 2,
    }


def render():
    root = PROJECT_ROOT / "docs/evidence/tract-study"
    try:
        data, metrics, checks, manifest, geometry = load_study(root)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"The saved tract study is unavailable: {exc}")
        return
    defaults = {"method": "K-means", "k": 2, "counties": sorted(data.countyname.unique()),
                "group": "All groups", "measure": "diabetes_pct", "range": (0.0, 100.0),
                "missing": True, "excluded": True, "filter_enabled": False}
    saved = st.session_state.setdefault("tract_controls", defaults.copy())
    saved.setdefault("filter_enabled", False)
    with st.sidebar:
        st.subheader("Tract study controls")
        st.caption("Changes update the results automatically. Hover over a ? for control help.")
        if st.button("Reset tract controls", help="Restore two-group K-means, all counties and "
                     "groups, Diabetes, both inclusion options, and no indicator filter."):
            saved.clear()
            saved.update(defaults)
            st.session_state.pop("tract_tutorial_step", None)
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
        st.subheader("Focus on an indicator (optional)")
        st.caption("Grouping uses all five indicators. This section only changes what you inspect.")
        measure = st.selectbox("Indicator to inspect", list(MEASURES), format_func=MEASURES.get,
                               **widget("measure"))
        filter_enabled = st.checkbox("Filter areas by this indicator", **widget("filter_enabled"))
        limits = st.slider("Keep estimates between (%)", 0.0, 100.0, step=0.5,
                           disabled=not filter_enabled, **widget("range"))
        missing = st.checkbox("Also include areas with no estimate", disabled=not filter_enabled,
                              **widget("missing"))
        if filter_enabled:
            st.caption(f"Showing {MEASURES[measure]} estimates from {limits[0]:g}% to "
                       f"{limits[1]:g}% (both endpoints included). "
                       + ("Areas with no estimate are also included." if missing else
                          "Areas with no estimate are hidden."))
        else:
            st.caption("No indicator filter: the range is ignored and areas with missing estimates "
                       "remain included. This indicator only sets the summary and map hover.")
        excluded = st.checkbox("Include excluded tracts", **widget("excluded"))
        st.caption("These controls select saved results. "
                   "They do not refit models or change inputs.")
    model = f"{'kmeans' if method == 'K-means' else 'ward'}_k{k}"
    full = model_view(data, model)
    visible = filter_view(full, counties, group, measure,
                          limits if filter_enabled else (0.0, 100.0),
                          missing if filter_enabled else True, excluded)
    selected = metrics.loc[metrics.model.eq(model)].iloc[0]
    st.header("Explore census tracts")
    st.caption("Version 1.1.0 · Guided tract exploration")
    st.subheader("What can I learn here?")
    st.write("Which small areas have similar combinations of health conditions and barriers "
             "to care—and how do individual areas differ? This page helps you explore those "
             "patterns before investigating local outreach needs.")
    st.markdown("**Clustering means grouping similar areas.** We compare five indicators "
                "together: diabetes, mental distress, lack of insurance, poverty and households "
                "without a vehicle. **K-means** is the sorting method: K means the number of "
                "groups, and means refers to their average profiles. It repeatedly assigns "
                "tracts to the nearest profile and updates those profiles. Indicators are "
                "put on comparable scales first. Here you are exploring saved results.")
    st.info("For a public health planner: similar profiles can suggest communities to compare "
            "when discussing outreach, benefits navigation or transportation support. "
            "Confirm local services, community priorities and data limitations before acting. "
            "The groups do not determine which intervention will work.")
    st.markdown("**Group numbers are names, not scores.** Group 1 is not first priority. "
                "Read the group profiles below to learn what each group actually looks like.")
    st.info("Grouping answers: Which areas have similar patterns across all five indicators? "
            "The optional indicator filter answers: Which areas meet a specific condition, "
            "such as a diabetes estimate of at least 20%? It narrows the map and table; "
            "it does not change community groups or their colors.")
    st.button("Start guided example: Apache County", on_click=tutorial_step, args=(1,),
              type="primary", help="Sets the controls for a three-step example using real "
              "public estimates. No uploaded data or models are changed.")
    step = st.session_state.get("tract_tutorial_step")
    if step:
        with st.container(border=True):
            st.subheader(f"Apache walkthrough · Step {step} of 3")
            if step == 1:
                st.write(f"**Start with an area.** The map now shows {len(visible)} Apache "
                         "County tracts. Each color identifies a community profile, not a "
                         "high-to-low risk score. Scroll to the map and compare the colors "
                         "with the group descriptions.")
                reference = full.loc[full.eligible].groupby("profile")[list(MEASURES)].median()
                for name, row in reference.iterrows():
                    st.write(f"{name}: statewide median diabetes {row['diabetes_pct']:.1f}%, "
                             f"uninsured adults {row['access2_pct']:.1f}%, "
                             f"poverty {row['poverty_pct']:.1f}%.")
                st.caption("These are medians across all Arizona tracts in each group—not "
                           "Apache County rates. All five indicators were used to form groups.")
                st.button("Next: focus on diabetes estimates", on_click=tutorial_step, args=(2,))
            elif step == 2:
                st.write(f"**Ask a specific question.** The controls now keep diabetes estimates "
                         f"of at least 20%. {len(visible)} Apache tracts match. This is an "
                         "illustrative filter, not a clinical or funding threshold.")
                st.write("Notice that the colors and group assignments stay the same. "
                         "Filtering selects areas to inspect; it does not run K-means again. "
                         "Use the tract table to compare insurance, poverty and vehicle access "
                         "instead of assuming every matching tract has the same barriers.")
                st.button("Next: interpret and save", on_click=tutorial_step, args=(3,))
            else:
                st.write("**Turn the pattern into a question for local review.** A planner "
                         "might ask: Do these areas have outreach services that residents can "
                         "reach, and what do community partners say is missing? The dashboard "
                         "does not answer that service-gap question on its own.")
                st.write("Open **Downloads & help** below and download the filtered tract data "
                         "and study receipt. They document the selected areas, filters and model. "
                         "Review source uncertainty before interpreting small differences.")
                st.success("You have learned to select an area, distinguish groups from "
                           "measurement filters, and prepare a documented shortlist for review.")
                st.button("Finish walkthrough", on_click=lambda: st.session_state.pop(
                    "tract_tutorial_step", None))
            st.caption("Changing a sidebar control ends the walkthrough. Reset tract controls "
                       "returns to the statewide view.")
    st.caption("ACS 2019–2023 · CDC PLACES 2025 release · 2023 tract boundaries · "
               f"Study {manifest['study_version']}")
    with st.expander("Start here: what are these groups?", expanded=True):
        st.markdown(
            "A **census tract** is a small statistical area. Here, **clustering** means "
            "sorting tracts into groups with similar patterns across five indicators: "
            "diabetes, frequent mental distress, uninsured adults, poverty, and households "
            "without a vehicle. Tracts in the same group can be far apart on the map.\n\n"
            "**K-means** is one way to do that sorting. The **K** means the number of groups. "
            "With two groups, the method looks for two representative profiles and assigns "
            "each eligible tract to the closer one. The indicators are put on comparable "
            "scales before calculating similarity.\n\n"
            "**Group 1 and Group 2 are identifiers, not rankings.** Group 2 is not necessarily "
            "worse, higher priority, or twice anything. Read the profiles below to see what "
            "distinguishes them. We retain neutral numbers because a group can have a mixed "
            "pattern, and its meaning can change with the method or number of groups.\n\n"
            "**New here? Keep K-means and two groups.** Choose a county, then compare the "
            "profiles and individual tract estimates. No knowledge of machine learning is needed."
        )
        st.caption("These are descriptions of communities, not diagnoses of residents. "
                   "Group membership alone does not establish where funding or services should go.")
    with st.expander("How to explore the map", expanded=False):
        st.markdown(
            "1. **Choose an area.** In Counties, clear the selections and choose a county "
            "such as Apache. The map, table, comparison choices, and download update together.\n"
            "2. **Optionally narrow the areas.** Choose an Indicator to inspect, then enable "
            "Filter areas by this indicator. For diabetes estimates of at least 20%, choose "
            "Diabetes and set Keep estimates between (%) to 20–100. Uncheck Also include areas "
            "with no estimate for known estimates only. Leave the filter off to explore all "
            "areas matching your county and group choices.\n"
            "3. **Understand the colors.** Read **What the groups look like** below. "
            "Each color identifies one group of similar tracts; it is not a low-to-high scale. "
            "Community group shows only that group. Choosing an indicator changes displayed "
            "estimates and, when enabled, the filter—not group colors. Leave the grouping method "
            "and "
            "number of groups at their defaults unless you want to compare alternatives.\n"
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
    st.info("County, group, and optional indicator filters narrow the view. Method and group count "
            "switch between ten previously fitted statewide models. Group numbers have no rank and "
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
    c.metric(f"Median: {MEASURES[measure]}", "Unavailable" if pd.isna(median) else f"{median:.2f}%")
    c.caption("Median across visible tracts, not population-weighted.")
    st.subheader("What the groups look like")
    st.caption(f"Current grouping: {method}, {k} groups. These profiles describe all eligible "
               "Arizona tracts in each group, even when the map is filtered to one county. "
               "Median means the middle tract value, not the percentage for the "
               "combined population.")
    profiles = full.loc[full.eligible].groupby("profile")[list(MEASURES)].median()
    sizes = full.loc[full.eligible].groupby("profile").size()
    for name, profile in profiles.iterrows():
        st.markdown(
            f"**{name} · {sizes[name]:,} tracts** — median diabetes estimate "
            f"{profile['diabetes_pct']:.1f}%; uninsured adults "
            f"{profile['access2_pct']:.1f}%."
        )
    with st.expander("Compare all five indicators"):
        st.dataframe(profiles.rename(columns=MEASURES).round(1), width="stretch")
    st.caption("The two figures above are a quick introduction; all five indicators define "
               "the grouping. Individual tracts can differ from their group's typical profile. "
               "Changing the method or group count updates these descriptions; Group 1 in "
               "one model is not necessarily the same set of tracts in another.")
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
        st.markdown("**Comparing methods (optional):** K-means finds representative group centers. "
                    "Ward hierarchical starts with separate tracts and repeatedly merges groups "
                    "whose combination adds the least variation within a group. More groups "
                    "gives a finer breakdown, not automatically a better answer.\n\n"
                    "**Stability** asks whether similar groupings appear when the study changes "
                    "its sample or indicators. A stable grouping can still have limitations. "
                    "These controls load saved analyses; they do not train a new model.")
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

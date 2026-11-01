# Tract dashboard guide

The **Explore census tracts** page is part of Community Health Operations Intelligence.
It describes groups of Arizona communities with similar health and social measures.
It does not predict individual illness, determine eligibility, or recommend funding.

## Open the dashboard

Run `streamlit run dashboard/app.py` from the repository root with the project's
environment activated. Open the local URL printed by Streamlit, then select
**Explore census tracts** in **Dashboard index**. The sidebar displays the application version. Version 1.1.0 includes the guided
example and optional indicator filtering.

The county pages still use their original scoring and allocation controls. The
tract page uses ACS **2019–2023**, CDC PLACES **2025 release**, and **2023 boundaries**.
These release labels do not imply a single observation year. Study version: **az-tract-v1**.

## Controls

Version 1.2.0 adds **Show HRSA health centers** inside **Map & tract details**.
It shows permanent active sites in your selected counties; mobile and seasonal
sites are optional. **Inspect a health center** highlights a facility and displays
its contact information. Facilities follow county selections only, independently
of tract group/indicator filters. A nearby point does not establish available care.
See `docs/HRSA_HEALTH_CENTERS.md` for the worked example and source methodology.

The page offers **Start guided example: Apache County** and **How to explore the map**.
Hover over the **?** beside any sidebar control for its purpose
and an example. Results update automatically; there is no Apply button.

| Control | What changes |
|---|---|
| Clustering method | Switches between saved K-means and Ward hierarchical assignments |
| Number of groups | Selects a saved statewide fit with 2–6 groups |
| Counties | Filters the map, tract table, comparison choices, and download |
| Community group | Shows all groups, one group, or excluded tracts |
| Indicator to inspect | Chooses the summary median and map-hover estimate; by itself does not filter areas |
| Filter areas by this indicator | Optional, off by default. Enables the percentage range and missing-value setting |
| Keep estimates between (%) | When enabled, retains estimates inside the inclusive range; 20–100 means at least 20% |
| Also include areas with no estimate | When filtering, keeps unknown estimates in addition to those inside the range |
| Include excluded tracts | Allows rows that could not enter the model to remain visible |
| Reset tract controls | Restores two-group K-means, all counties/groups, diabetes, and turns the indicator filter off |

Grouping finds similar patterns across all five indicators. The optional filter narrows
the areas to a specific condition; it never changes groups or map colors. When it is off,
the range and missing-value controls are disabled and ignored. County, community-group
and excluded-tract selections still apply. Turning the filter back on restores its saved
range. The study receipt records whether the indicator filter was enabled.

These controls **do not retrain models**, change feature weights, or calculate new
health estimates. Method/group-count changes select one of ten evaluated saved fits.
County and range filters do not change statewide group assignments or medians.
Group 1 in one model is not necessarily equivalent to Group 1 in another.
Selections persist when navigating to another dashboard page and back.

The three summary cards show the number of filtered tracts, filtered exclusions,
and the selected measure's median across visible estimates. This median gives each
tract equal weight; it is not population-weighted prevalence.

## Map & tract details

Colors identify groups; gray indicates excluded tracts. Zoom/pan and hover to inspect
tract IDs, county, selected measure, and exclusion reason. The blank background does
not require map tiles. Generalized boundaries are unsuitable for travel distances.
Use the table below the map as a text alternative.

Select **First tract** and **Comparison tract** to inspect source estimates side by
side. Both choices come from the filtered table; selecting the same tract twice
shows it once. Tract IDs retain their leading zero.

The uncertainty table contains:

- `diabetes_crude95ci`, `mhlth_crude95ci`, `access2_crude95ci`: modeled 95% intervals.
- `B17001_M001`, `B17001_M002`: ACS 90% margins of error for the poverty denominator
  and numerator counts.
- `B08201_M001`, `B08201_M002`: ACS 90% margins of error for total households and
  households without a vehicle.

The ACS count margins are **not** percentage margins. Derived-rate uncertainty is
not calculated. Negative source status codes and blank values are unavailable
information, not zero estimates. Different measures describe different populations:
for example, uninsured adults aged 18–64 versus all households for vehicle access.

Statewide profile medians use all 1,730 eligible tracts and stay fixed during
filtering. Individual tracts may differ substantially from those medians.

## Stability & methods

Review all ten candidates and the individual perturbation results for the currently
selected model. **Silhouette** summarizes separation. **Adjusted Rand index (ARI)**
compares two sets of assignments; 1 means identical grouping even if labels change.
Neither is predictive accuracy. Subsamples, omitted features/counties, alternative
scaling, and initialization checks answer different questions.

Only two-group K-means passed the project's prespecified heuristics in this study.
Other selections show a warning and remain available for comparison. Passing those
heuristics does not prove that communities form natural categories. PLACES estimates
include ACS inputs, crude rates reflect age composition, and source uncertainty was
not propagated through the clustering.

## Downloads & help

**Download filtered tract data** exports the current rows, selected profile labels,
source values, uncertainty fields, exclusions, and saved assignments. **Download
study receipt** records the selected model, controls, row count, CSV hash, and model
manifest. Keep the receipt with the CSV. **Download model comparisons** saves the
statewide evaluation table, unaffected by geographic filters.

Open the guide/tutorial expanders on this tab for instructions. If a download fails,
wait for the page to finish updating and click again; check the browser's downloads
list. An empty filter intentionally produces a header-only data file and zero-row
receipt. A checksum error when loading the study requires rebuilding/restoring its
saved artifacts, not ignoring the error.

If a tract is missing from your choices, reset the controls and include exclusions
and missing values. A tract outside Arizona or outside the 2023 geography is not in
this study. If the map is unavailable, use the table and CSV. If nothing matches,
broaden the range, select a county, or reset.

**Glossary:** tract = Census statistical area; profile = descriptive cluster;
modeled estimate = estimate produced using a statistical model; exclusion = tract
retained in the data but omitted from fitting; sensitivity = how a result changes
when an analysis choice changes.

## Understanding clustering and group labels

A census tract is a small statistical area. Clustering sorts tracts with similar patterns across five indicators: diabetes, frequent mental distress, uninsured adults, poverty and households without a vehicle. Similar tracts need not be geographically adjacent.

K-means looks for K representative group profiles and assigns eligible tracts to the nearest one after putting the indicators on comparable scales. K=2 means two groups. Ward hierarchical builds groups by repeatedly merging those whose combination adds the least within-group variation. These controls select saved results; they do not retrain models.

Group 1, Group 2 and other numbers are neutral identifiers, not risk ranks. A group may have mixed characteristics. Its meaning can also change when you switch method or number of groups. Do not assume that Group 1 in one model equals Group 1 in another.

Read **What the groups look like** above the map. It shows the number of tracts and median diabetes and uninsured rates for each selected-model group. Expand **Compare all five indicators** for the complete profile. These values describe the full eligible Arizona cohort and do not change when you filter counties. A median is the middle tract estimate, not the combined population rate. Individual tracts can differ from the group median.

For a first visit, keep K-means and two groups, choose a county, and compare its tracts. Colors identify groups; they are not a low-to-high scale and do not switch to the selected Measure. More groups is a finer breakdown, not automatically a better result. Stability asks whether similar groupings remain when samples or indicators change. Group membership alone does not establish individual health risks or funding priorities.

## Follow the guided Apache example

On **Explore census tracts**, select **Start guided example: Apache County** near the top of the page. The walkthrough sets the controls for you and uses the bundled public estimates.

1. **Read the groups.** Start with Apache County and K-means with two groups. See the 18 tracts and read what map colors mean. The group summaries describe statewide profiles, not Apache County rates.
2. **Focus on diabetes estimates.** Select **Next: focus on diabetes estimates**. The range changes to 20–100% and the tutorial explains the resulting count. This is an illustrative filter, not an official intervention threshold; it does not refit the model.
3. **Interpret and save.** Select **Next: interpret and save**. Review the example planning question, compare individual estimates and uncertainty, then use **Downloads & help** to save the filtered CSV and study receipt.

**Finish walkthrough** closes the guide and keeps your current filters. Changing sidebar controls ends the guided mode so its instructions cannot describe stale settings. **Reset tract controls** restores the statewide view. Use the results to frame local questions about outreach and access barriers; group membership does not establish which intervention will work.

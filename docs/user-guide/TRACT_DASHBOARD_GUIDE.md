# Tract dashboard guide

The **Explore census tracts** page is part of Community Health Operations Intelligence.
It describes groups of Arizona communities with similar health and social measures.
It does not predict individual illness, determine eligibility, or recommend funding.

## Open the dashboard

Run `streamlit run dashboard/app.py` from the repository root with the project's
environment activated. Open the local URL printed by Streamlit, then select
**Explore census tracts** in **Dashboard index**. The current integration is local;
the public deployment has not been updated or verified for this feature.

The county pages still use their original scoring and allocation controls. The
tract page uses ACS **2019–2023**, CDC PLACES **2025 release**, and **2023 boundaries**.
These release labels do not imply a single observation year. Study version: **az-tract-v1**.

## Controls

The page opens with **How to use the controls**, a five-step walkthrough you can
collapse when ready. Hover over the **?** beside any sidebar control for its purpose
and an example. Results update automatically; there is no Apply button.

| Control | What changes |
|---|---|
| Clustering method | Switches between saved K-means and Ward hierarchical assignments |
| Number of groups | Selects a saved statewide fit with 2–6 groups |
| Counties | Filters the map, tract table, comparison choices, and download |
| Community group | Shows all groups, one group, or excluded tracts |
| Measure | Chooses the percentage used by the range filter, summary median, and map hover |
| Measure range (%) | Retains estimates inside the inclusive range |
| Include missing measure values | Keeps unknown estimates even when a numeric range is set |
| Include excluded tracts | Allows rows that could not enter the model to remain visible |
| Reset tract controls | Restores two-group K-means, all counties/groups, diabetes, full range, and both inclusion options |

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

# Arizona tract analysis and dashboard plan

Agreed direction: October 24, 2026. The initial tract acquisition and tabular join
audit are implemented; see [source audit](TRACT_DATA_AUDIT.md). Polygon identifiers
now match exactly, and the first clustering comparison is complete; see the
[model report](TRACT_MODEL_REPORT.md). The tract page is now integrated into the original
dashboard with a [guide](user-guide/TRACT_DASHBOARD_GUIDE.md) and
[worked tutorial](user-guide/TRACT_DASHBOARD_TUTORIAL.md). Public release remains pending.

## Research question

Do Arizona census tracts form stable groups with different combinations of health burden and barriers to care?

The study is descriptive. Cluster membership is not a diagnosis, eligibility rule, causal explanation, or validated funding recommendation. Preserve the county planning dashboard and its historical AWS evidence as separate work. The county CSV comparison functions remain reusable for later service-data studies; do not distribute county contact counts across tracts.

## Delivery sequence

1. **Data audit and pinned sample.** Identify exact ACS 5-year and CDC PLACES tract releases, variables, observation periods, boundary versions, uncertainty fields, and download endpoints from official documentation. Save a source register and raw-file hashes. Start with Arizona and matching tract boundaries. Keep a full join report, including missing/unmatched tracts. No clustering until the join and measure definitions have been checked.
2. **Exploration.** Produce tract counts, missingness tables, distributions, correlations, and maps. Retain ACS margins of error and PLACES intervals with their confidence levels. Treat suppression codes as statuses, not values. Label PLACES measures as modeled estimates. Compare usable and excluded tracts before deciding how to handle missingness.
3. **Feature decisions.** Select a small set representing distinct concepts. Record units, population universes, rationale, and any exclusions. Avoid giving a concept extra weight by including several near-duplicate measures. Do not include tract IDs, coordinates, existing priority scores, or SVI composite rankings as clustering features. Coordinates support mapping and geographic checks.
4. **Clustering study.** Compare standardized K-means with a hierarchical approach. Examine a modest range of cluster counts, feasible for the eligible sample, rather than selecting a visually appealing answer. Fix random seeds, record preprocessing, inspect group size and profiles, and compare separation metrics with stability under resampling and feature changes. Fit preprocessing within each resampling run. Use label-invariant stability measures; cluster numbers have no ordered meaning.
5. **Interpretation and limitations.** Describe groups using observed profiles. Examine how groups differ by geography and by missingness/uncertainty. Keep 'no useful stable grouping' as a valid finding. Do not select features or cluster counts to force a preferred geographic narrative. Any predictive task later needs a separate outcome and geographic/time-aware evaluation design.
6. **Dashboard.** Add a tract study view with source context, exploration, group profiles, stability results, and downloads. Keep the Arizona county template clearly separate. Expensive analysis runs in a reproducible build, not on every dashboard interaction. Controls must distinguish filtering the displayed results from refitting the model.
7. **Documentation and tutorial.** Complete the user guide and worked tutorial below, using screenshots and results from the finished version. Verify each instruction against the dashboard. Add a technical reproduction guide and analysis report.
8. **Portfolio release.** Package a short walkthrough and one research finding with evidence. Publish claims about clustering only after the analysis and dashboard checks pass. Retain the limitations when sharing on LinkedIn.

## Initial source shortlist

- ACS 5-year: population, poverty, income, age structure, vehicle access, insurance, or disability. Select exact fields and denominators during the audit.
- CDC PLACES: a small set of tract-level health measures with available uncertainty fields. Confirm underlying observation years separately from release years.
- Census tract boundaries: a version compatible with both sources, with geography exclusions recorded.
- HRSA health-center locations: later extension after the tract study works. Proximity to included sites does not measure capacity or travel time.

Official starting points already reviewed in the project discussion:

- https://www.census.gov/data/developers/data-sets/acs-5year.html
- https://www.cdc.gov/places/methodology/index.html
- https://www.cdc.gov/places/about/
- https://data.hrsa.gov/data/download

Endpoints, variable codes, and release compatibility must be verified during acquisition. This plan does not designate an unverified release as current.

## Dashboard screens

| Screen | User question | Required behavior |
|---|---|---|
| Start here | What can I learn from this study? | Explain the study, eligible geography, modeled versus survey estimates, and interpretation limits |
| Data and coverage | What data went into the analysis? | Source periods, definitions, uncertainty, missing/excluded records, and join counts |
| Explore tracts | How do conditions vary? | Map and table with tract identifiers, county filters, selected measures, units, and missingness |
| Community profiles | Which tracts have similar profiles? | Group profiles in original units, group sizes, and individual tract details; no ordinal risk labels |
| Stability and assumptions | How much do the findings depend on choices? | Saved model comparisons, feature/preprocessing choices, stability results, and known weak groupings |
| Download and reproduce | How can someone check this work? | Filtered tables, source register, analysis settings, model version, and clear reproduction instructions |

Filtering must retain the original fitted model and group assignments unless the user explicitly starts a separate analysis. Explain this beside the controls. Unknown/excluded tracts stay visible as a separate category. Use accessible colors and a table alternative to maps.

## Required user documentation

Create `docs/user-guide/TRACT_DASHBOARD_GUIDE.md` with:

- Purpose and audience; what the dashboard can and cannot establish.
- How to open the published app and run it locally.
- A screen-by-screen explanation of controls, values, and downloads.
- How to find a tract and read its community profile.
- How missing data, margins of error, and modeled estimates appear.
- Why cluster labels do not rank communities and why filters do not retrain the model.
- Common problems: empty filters, missing tract, unavailable measure, and failed download.
- Data/version information and a glossary written for a nontechnical researcher.

Create `docs/user-guide/TRACT_DASHBOARD_TUTORIAL.md` after the working analysis exists. It must walk through a real, reproducible example:

1. Read the study scope and source periods.
2. Filter to a county and locate a tract from the pinned release.
3. Compare selected measures with another tract, including uncertainty where available.
4. Inspect both group profiles and explain why individual tracts can differ from a group average.
5. Examine a stability result and state how it affects the interpretation.
6. Download the comparison and identify the source/model versions.
7. Write a short finding and one limitation supported by the displayed results.

Use actual expected values and screenshots from a named release. Include a reset step, approximate walkthrough duration measured during verification, and an answer/example for each interpretation task. Do not fabricate findings or screenshots while the dashboard is still planned.

## Technical documentation

Record acquisition commands, environment/dependency versions, feature definitions, exclusions, preprocessing, model settings, evaluation method, reproducibility steps, and checksums. Keep a decision log explaining changes. Separate uncertainty in input estimates from instability in clustering; neither is a probability of individual illness.

## Release completion criteria

- Raw-to-analysis pipeline can be rerun from pinned inputs with matching documented outputs.
- Geography and join checks account for all records without silent loss or duplication.
- A reviewed analysis report supports the displayed group descriptions, including weak or negative findings.
- Dashboard filters, empty states, group labels, downloads, and version information pass tests and browser review.
- Existing county dashboard regression checks pass in a supported environment; the prior local startup issue is resolved or explicitly isolated.
- A user can complete the tutorial without code edits or verbal instructions; discrepancies are corrected in both guide and app.
- Portfolio descriptions distinguish built, evaluated, and proposed capabilities.

# Arizona tract clustering: first study

Study version **az-tract-v1**, October 24, 2026. This saved analysis is now integrated
into the original dashboard's **Explore census tracts** page. See the
[dashboard guide](user-guide/TRACT_DASHBOARD_GUIDE.md) and
[worked tutorial](user-guide/TRACT_DASHBOARD_TUTORIAL.md). Public release is pending.

## Finding

Of ten candidates, **K-means with two groups** was the only one to pass the project
rules recorded before fitting. It separates tracts into two broad profiles across
the five selected measures. That does not establish two naturally occurring types
of community, a clinical classification, or a validated allocation rule.

The 2023 cartographic boundary file matches all **1,765** joined tract identifiers.
The five-feature model uses **1,730** tracts and retains **35** excluded tracts with
reasons in its output. The earlier six-candidate audit had 1,725 complete rows;
removing income from the primary feature set makes five additional tracts eligible.
No missing values were imputed. Each tract receives equal weight.

Excluded tracts contain a combined ACS population estimate of **26,261**, compared
with **7,241,914** in eligible tracts. Missingness therefore affects inhabited areas
and must remain visible in the dashboard.

| Check | Two-group K-means result |
|---|---:|
| Silhouette | 0.4361 |
| Median ARI across 20 subsamples | 0.9911 |
| Tenth-percentile subsample ARI | 0.9728 |
| Minimum ARI after removing a feature | 0.8146 |
| ARI with RobustScaler | 0.8948 |
| ARI replacing poverty with income, common rows | 0.7960 |
| Minimum ARI after leaving out a county | 0.7735 |

ARI measures agreement between two assignments after accounting for chance; 1 means
identical grouping even if the numeric labels change. These checks do not measure
predictive accuracy or propagate the uncertainty in the original estimates.

The lowest county-omission agreement occurs when Maricopa County is removed,
leaving 742 eligible tracts in that comparison. This is a substantial change in
the study population, and it shows that statewide grouping depends partly on
which communities are included.

Two-group Ward clustering had a slightly higher silhouette, **0.4479**, but a median
subsample ARI of **0.6233** and minimum feature-removal ARI of **0.2836**. Selecting on
separation alone would therefore have preferred a much less stable candidate.
K-means with more groups also failed at least one prespecified rule. The complete
comparison is saved, including the unsuccessful candidates.

## Profiles in original units

Values below are **medians across tracts**, not population-weighted prevalence.
Group numbers are arbitrary identifiers and have no ordered meaning.

| Measure (%) | Group 1: 1,228 tracts | Group 2: 502 tracts |
|---|---:|---:|
| Modeled adult diabetes | 10.00 | 14.35 |
| Modeled frequent mental distress | 14.50 | 18.40 |
| Modeled uninsured adults aged 18–64 | 9.00 | 21.25 |
| People below poverty | 7.48 | 24.12 |
| Households without a vehicle | 2.32 | 9.04 |

Group 2 has higher medians on these selected measures, but an individual tract can
differ substantially from its group's median. Population universes differ among
measures. Do not relabel these as individual risk groups or claim the clustering
establishes a cause of the observed differences.

## Tools and methods

- **pandas/NumPy:** joined data, eligibility, exploratory summaries, and saved tables.
- **scikit-learn:** StandardScaler, KMeans (30 initializations), Ward
  AgglomerativeClustering, silhouette, adjusted Rand index, and RobustScaler sensitivity.
- **PyShp:** official Census boundary reading and exact identifier reconciliation.
- **Plotly:** interactive comparison charts, profiles, and tract map.

The primary features are diabetes, frequent mental distress, uninsured adults,
poverty, and households without vehicles. Every subsample and sensitivity fit learns
its own scaling parameters. The [decision record](TRACT_MODEL_DECISIONS.md) explains
selection rules and limitations. The model manifest records versions, seed, settings,
input hashes, and output hashes. This study does not use prediction, neural networks,
or PCA; these were not needed to answer the current descriptive question.

## Read and reproduce

Open [the interactive analysis report](evidence/tract-study/models/analysis.html) in
a browser. Inspect all ten candidates, the selected model's sensitivity results,
original-unit profile medians, and map. Hover for tract details. Legend filtering
changes what is shown; it does not refit a model. Excluded tracts appear in gray.
This report is an analysis artifact, not the finished dashboard tutorial.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,analysis]"
.\.venv\Scripts\python.exe scripts/tract_data_audit.py
.\.venv\Scripts\python.exe scripts/tract_boundaries.py
.\.venv\Scripts\python.exe scripts/tract_model_study.py
.\.venv\Scripts\python.exe scripts/tract_study_figures.py
```

The first two commands after installation can access public sources if the cache is
absent. The model and figure builds use local audited inputs. Fresh upstream downloads
may change; check source hashes before comparing results. Exact numerical replay
requires the versions recorded in `model_manifest.json`, including NumPy/SciPy.

Saved files under `docs/evidence/tract-study/models/` include every candidate's
assignment, model comparisons, individual perturbation scores, selected profiles,
county coverage, group statistics, and the manifest. `tract_profiles.csv` retains
source estimates, component margins of error, CDC intervals, and exclusion reasons.
The map uses generalized display boundaries; it is unsuitable for measuring travel
distance, service catchments, or parcel-level locations.

## Limits and next delivery

PLACES estimates are modeled and include ACS inputs. Correlations with ACS variables
can partly reflect that modeling process. Crude health rates also reflect age
composition. ACS component margins of error and CDC confidence intervals are retained,
but derived-rate margins of error and uncertainty propagation are omitted in this
first model. Missingness can exclude populated tracts and is not random by assumption.

County omission and alternative scaling still change some assignments. The passing
rules are project heuristics, not a scientific guarantee of stable underlying groups.
The result supports further descriptive exploration, not operational allocation.

The integrated tract page now exposes these saved results, uncertainty, and exclusions.
The county dashboard remains a separate view. Public release and portfolio publication
still require deployment verification.

## Verification

All **86 non-dashboard tests** pass, including six new modeling checks. Repository
lint and diff whitespace checks pass. A second complete model run reproduced every
CSV and manifest hash exactly in this environment. This does not establish identical
results under different dependency versions. Existing Streamlit startup checks were
not rerun here; the local Windows startup issue remains recorded in CURRENT_STATUS.

The standalone report was checked in headless Edge: four Plotly figures rendered,
including the tract map, with no JavaScript page errors. All four screenshots were
visually inspected; group colors match across the profile chart and map. Reproduce
that check by serving the model directory on localhost port 8766 and running
`scripts/verify_tract_report.py --channel msedge` with Playwright 1.58.0 installed.
This report check does not substitute for the future dashboard's UI tests.

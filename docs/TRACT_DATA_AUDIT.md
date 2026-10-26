# Arizona tract source audit

This is the acquisition and exploration stage of the tract study. No clustering
results or new dashboard capabilities are claimed here.

## Sources and timing

Use the CDC PLACES **2025 census tract GIS-friendly release**, dataset `yjkw-uj5s`.
The [official release description](https://catalog.data.gov/dataset/places-census-tract-data-gis-friendly-format-2025-release)
specifies 2023 tract boundaries. Release year does not mean every input was observed
in that year. Selected diabetes, frequent mental distress, and uninsured-adult
estimates are model-based prevalence estimates; their source intervals are 95%.
The release uses BRFSS, Census and ACS inputs. Associations with ACS features can
partly reflect the PLACES modeling process rather than independent observations.

Pair it with the **2019–2023 ACS five-year detailed tables**. Download the
[official table-based summary files](https://www.census.gov/programs-surveys/acs/data/summary-file.2023.html).
The API returned a Missing Key HTML page during acquisition; the public summary
files provide an alternative without a key. API group metadata remains accessible.
Do not substitute a different ACS vintage silently.

| Candidate or context | Source | Interpretation |
|---|---|---|
| Population, context only | B01003, line 1 | Total population; not a clustering feature |
| Median household income | B19013, line 1 | Household income in 2023 inflation-adjusted dollars |
| Poverty percentage | B17001, line 2 / line 1 | People below poverty / population for whom poverty status is determined |
| No-vehicle percentage | B08201, line 2 / line 1 | Households with no vehicle / all households |
| Diabetes percentage | PLACES DIABETES | Modeled crude adult prevalence |
| Frequent mental distress percentage | PLACES MHLTH | Modeled crude adult prevalence |
| Uninsured percentage | PLACES ACCESS2 | Modeled crude prevalence among adults aged 18–64 |

These are candidates for exploration, not six automatically approved features.
Income and poverty may duplicate a concept; review their correlation and the
effect of retaining one or the other before fitting. Crude health estimates also
reflect age composition. The population universes differ across measures.

## Reproduce acquisition and audit

From the repository root with its environment installed:

```powershell
.\.venv\Scripts\python.exe scripts/tract_data_audit.py
```

Raw downloads are cached under `data/raw/tract-study-2026-10-24/`, excluded from
Git. Each has a retrieval receipt. Repeated runs reuse those exact files. For a
deliberate refresh, provide a different `--raw` directory and `--out` directory;
compare hashes and coverage before adopting it. A fresh download from an upstream
URL is not guaranteed to reproduce the earlier bytes.

Outputs under `docs/evidence/tract-study/`:

- `source_audit.json`: URLs, retrieval times, file hashes, counts and limitations.
- `tract_join_audit.csv`: full outer join, source fields, cleaned candidate values,
  match status, completeness and missing-feature reasons for every observed tract.
- `acs_variable_definitions.json`: selected official variable definitions.
- `county_coverage.csv`: complete/incomplete candidate rows by county.
- `candidate_distributions.csv` and `candidate_correlations.csv`: exploratory summaries.

The import reads identifiers as strings, selects Arizona census tracts rather than
block groups, rejects duplicate IDs, and joins one-to-one without dropping unmatched
records. Negative values and nonnumeric Census status strings remain in raw source
columns and become missing only in the additional numeric columns. Zero denominators
do not produce a rate. No imputation or weighting is performed.

ACS source margins of error are retained alongside estimates. Derived poverty and
vehicle percentages do not yet have calculated margins of error. Input uncertainty
is separate from future clustering stability. Completeness does not imply precision.

## October 24 findings

The saved join contains **1,765 ACS tracts**, of which **1,740 match PLACES**.
The remaining 25 have no PLACES row; there are no PLACES-only identifiers.
Across all six candidate features, **1,725 tracts have complete values** and 40
have at least one missing candidate. These are candidate coverage counts, not a
final modeling cohort. All 40 have unavailable median household income; the raw
Census sentinel values remain visible. Several excluded tracts have zero population,
but some have thousands of residents, so exclusion cannot be described simply as
removing unpopulated tracts.

Pairwise Pearson correlations include poverty versus income **−0.653** and poverty
versus frequent mental distress **0.716**. These descriptive associations do not
establish causes or validate PLACES estimates. The correlation file uses pairwise
available observations, so different pairs may use different tract sets.

The Census key supplied separately by the user was verified with a small official
API request. It was not stored in this repository, request receipts, or outputs.
This snapshot uses the already-started public bulk downloads.

Verification: four new parser/geography tests pass, and all **80 non-dashboard
tests** pass. Ruff passes for the added script and tests. Dashboard startup checks
remain subject to the Windows issue recorded in CURRENT_STATUS; no dashboard
change was made during this acquisition stage.

## Remaining gates before modeling

Verify polygon geography against the joined IDs; inspect excluded tracts and source
status codes; calculate or explicitly omit derived-rate uncertainty; review candidate
redundancy, skew and population universes; then run standardized K-means and Ward
hierarchical comparisons with resampling and feature sensitivity. Keep excluded
tracts visible. A weak or unstable grouping is an acceptable study result.

The final dashboard guide and worked tutorial remain required by
[the delivery plan](TRACT_ANALYSIS_PLAN.md). Write their expected values and screenshots
from the working dashboard, after these analysis gates pass.

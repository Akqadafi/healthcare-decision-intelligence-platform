# Step 2 — county CSV workflow

Implemented locally October 27, 2026. Not pushed or deployed publicly.

The dashboard now includes Outreach workbench: synthetic or bundled public county context, county/month/program scope, explicit thresholds, CSV upload and confirmed column mapping, validation errors, match accounting, period review, comparison table and CSV/JSON/Markdown downloads. The guide is downloadable from the page. A reset clears workbench widgets and renews the upload input.

The context contract now supports observation-period ranges, preserving multi-year ACS dates instead of representing them as one month. Public comparisons require a rationale. Source manifests, source/input/result checksums and a code fingerprint appear in the receipt. Uncertainty intervals absent from the county mart are explicitly unavailable.

## Evidence

- Existing 37 workbench tests passed after the period-contract extension.
- Eleven new tests cover malformed previews, mapping, multi-year compatibility, export hashes, formula-safe text, confirmation invalidation, reset and public-context review.
- Full regression run: 102 tests passed, including county and tract dashboard tests. Streamlit tests required execution outside the sandbox because startup stalled inside it.
- Browser on localhost:8503 accepted outreach_SYNTHETIC.csv through the file chooser. Public context blocked results without a period rationale. Synthetic context produced Apache 1, Cochise 4, Coconino 0 contacts per 1,000; Maricopa remained unknown. Export controls appeared and the CSV download action was exercised.
- Screenshot saved in the Applications workspace as workbench-step2-preview.png.
- Pytest emitted a pre-existing cache-directory warning; test assertions passed.

## Remaining release gates

This is the county CSV increment. Tract/XLSX/site uploads, map workspace, HRSA layers, saved-study restoration, confidential-data support and national expansion are not implemented here. Public-host concurrency/resource measurements and deployment remain separate gates. No Docker build or cloud deployment was performed. Workbench controls can reset when navigating away; export before leaving.

Use docs/user-guide/WORKBENCH_GUIDE.md for the worked tutorial. The first example intentionally uses synthetic data; users must not treat its counts as actual outreach outcomes.

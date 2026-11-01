# Changelog

Application changes are separate from public dataset releases and saved model versions.
Unreleased entries describe local work; they do not establish public deployment.

## 1.2.0 — 2026-11-01

- Added optional HRSA health-center locations to tract exploration, filtered by selected counties.
- Permanent sites shown by default; mobile and seasonal listed addresses are optional.
- Added facility selection/highlighting, address and phone details, coordinate-quality notes and an accessible table.
- Bundled a validated Arizona snapshot: 264 active sites (208 permanent, 30 mobile, 26 seasonal), retrieved November 1, 2026. Source update date is not exposed.
- Added refresh script, integrity/geography/coordinate checks and regression tests. Facility locations do not change models or scores.
- Deployment verification pending; see docs/HRSA_HEALTH_CENTERS.md.

## 1.1.0 — 2026-11-01

### October 28 — explain tract groupings
- Made indicator filtering optional and off by default; renamed controls, explained inclusive percentage ranges, and distinguished inspecting an indicator from five-indicator clustering. Updated the walkthrough, guide and regression checks.
- Added visible definitions, public health interpretation and a three-step Apache walkthrough that sets filters and explains results. Added a visible preview update date to help identify stale local pages.
- Added a beginner explanation of census tracts, clustering, K-means and neutral group IDs.
- Added live statewide group profiles above the map, with counts, median diabetes and uninsured rates, and an expandable five-indicator comparison.
- Explained Ward, stability, map colors and why changing models can change group identities.
- No model assignments, features, group counts or public data were changed.

### Added
- County CSV outreach workflow, validation, observation-period ranges and reproducible exports.
- Guided example and upload paths; exact Arizona county-name/code matching.
- One downloadable report package containing a brief, table and provenance.

### Changed
- Replaced the long workbench form with task selection, spreadsheet setup and results.
- Recognized common column names and read program/month from the uploaded file.
- Moved technical details and geographic scope into optional sections.
- Added plain-language summaries, population-normalized activity chart and readable column labels.
- Made criteria-based highlighting opt-in; disabled criteria are omitted from exported flags.
- Updated the user guide with contextual help and limitations.

### Release status
- Version 1.1.0 published to Streamlit and verified November 1, 2026; PR #2, commit 285a52f.
- Existing county scores, public snapshots and saved tract models are unchanged.
- Verification and deployment evidence: docs/RELEASE_1.1.0.md.

# Community Health Operations Intelligence — updated delivery plan

Updated October 27, 2026. This roadmap supersedes the October 14 workbench sequence. New features below are planned, not implemented. The older workbench plan remains a reference for detailed validation and reproducibility requirements.

## Product objective

Help public health analysts and community organizations compare community conditions with their own service activity, explore relevant service locations, and export an evidence-backed planning brief.

Flagship question: Where do selected community needs coincide with low recorded outreach activity, and which areas deserve further investigation?

Low recorded activity is not proof of unmet need, program failure, or intervention effectiveness. The first release covers Arizona. National coverage follows a usable, evaluated Arizona workflow.

## What we can reuse

- Existing county dashboard, planning controls, deterministic scores and allocation scenarios.
- ACS/CDC tract data and boundaries, saved K-means/Ward models, stability results and tract exploration.
- The 1,730-tract eligible study, including records of excluded areas.
- Tract guides, tutorial, filtered CSV and receipt downloads.
- County CSV parsing/comparison logic in src/healthcare_di/workbench.py, its tests and synthetic demonstration.
- Existing Streamlit deployment and portfolio.

The upload wizard, integrated service layers and full planning-brief journey remain development work. Check current source and deployed behavior at implementation start; old test counts are not fresh verification.

## First-release experience

Use the Acres interaction pattern as inspiration: a central map, selectable layers, search, linked filters and a selected-location details panel. Use original design and public health content.

Workflow:
1. Choose an Arizona county or tract study and reporting period.
2. Select a public measure; inspect its definition, units, population and dates.
3. Upload aggregate service data and confirm column mappings.
4. Review validation, geographic matches, duplicates and period compatibility.
5. Explore a map linked to a table and community details.
6. Add service locations, select several communities and compare them.
7. Export a planning brief with results, sources, decisions and limitations.

Provide an accessible table alternative and a tile-free fallback. Keep missing/excluded areas visible. Search initially uses supported county/tract names and IDs; address geocoding and drawing arbitrary boundaries come later.

## User uploads

Start with county CSV using the existing tested logic, then add tract CSV, bounded XLSX with sheet selection, and non-sensitive service-location files.

Community files require geographic ID, period, program, measure and counting unit. Site files require latitude/longitude and site description; optional capacity values need definitions and dates.

Required behavior:
- Preserve five-digit county FIPS and eleven-digit tract GEOIDs as strings.
- Confirm mappings; block ambiguous geography and many-to-many joins.
- Account for every uploaded row; retain unmatched rows and reasons.
- Keep missing activity distinct from explicit zero.
- Require explicit aggregation rules; do not average percentages without denominators.
- Never distribute county contacts across tracts or silently translate ZIP codes to tracts.
- Record boundary vintage, observation period, release date, units and population universe.
- Review temporal mismatches; block incompatible geographic levels.
- Validate coordinates and study-area coverage. Facility location does not establish client residence.
- Replacing a file or mapping invalidates dependent results.

Begin with provisional limits of 10 MiB and 100,000 rows; validate actual memory and concurrency before committing to them. Bound XLSX decompression and parsed dimensions, reject macros, never execute formulas or uploaded code, and make spreadsheet exports formula-safe.

The public demo accepts public/synthetic aggregate statistics and non-sensitive service locations. Design for isolated session state, no shared upload cache, no permanent upload storage, no uploaded records in logs, and a clear reset action. Verify these properties before launch. Uploads reach the server; do not promise on-device processing or confidential-data suitability. Patient records, names and individual home addresses are outside this version.

## Public data sequence

| Order | Dataset | Purpose and integration requirement |
|---|---|---|
| Foundation | Existing ACS and CDC PLACES | Preserve source definitions, uncertainty, modeled-estimate labels and geographic compatibility |
| First addition | HRSA Health Center Service Delivery Sites | Add service-location context; verify coordinates, status and Arizona coverage. Proximity is not capacity, affordability or travel time |
| Next | HRSA Health Professional Shortage Areas | Show designation type and geography accurately; do not treat all designations as tract measures |
| Next | CDC/ATSDR Social Vulnerability Index | Contextual layer with vintage recorded; avoid double counting overlapping ACS inputs |
| Next | USDA Food Access Research Atlas | Audit release, food-access definitions and tract vintage before joining |
| Later | CDC heat tracking and suitable ADHS datasets | Develop an Arizona heat-outreach use case; retain each measure's real geography and period |
| Later | Census Community Resilience Estimates | Emergency-preparedness context; clarify how it differs from SVI |

Official source entry points:
- https://data.hrsa.gov/data/download
- https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
- https://ers.usda.gov/data-products/food-access-research-atlas/download-the-data
- https://www.cdc.gov/environmental-health-tracking/php/data-research/tracking-heat-events.html
- https://data.azdhs.gov/dashboards/home
- https://www.census.gov/programs-surveys/community-resilience-estimates.html

These are candidates, not guarantees of compatible downloadable releases. Before adding any layer, record exact variables, definitions, units, geography/vintage, observation dates, release date, uncertainty, missing/suppressed statuses, use conditions, retrieval metadata and checksums. Acquire validated snapshots outside user sessions. Failed refreshes retain the previous validated release.

## Analysis and machine learning

Separate raw community measures, deterministic county planning scores, and descriptive tract clusters. Clusters are not ordered risk tiers or funding recommendations.

Support compatible population-normalized activity measures and explicit investigation thresholds. Contacts per 1,000 residents are not the percentage of eligible people served. Do not sum repeated contacts and call them unique people.

Filtering saved models does not refit them. Display existing stability results and original-unit profiles. Uploaded data and new public layers do not automatically become model features. Model expansion requires a new feature rationale, missingness/overlap audit and stability evaluation. Prediction requires observed outcomes and appropriate held-out evaluation; it is not a first-release requirement.

## Delivery phases and completion gates

| Phase | Work | Completion gate |
|---|---|---|
| 0: Baseline and study design | Inspect reusable code; define study/receipt schema; create county, tract and service-site synthetic templates; sketch screens | Current baseline checked; example outputs and counting rules documented; fixtures include missing, zero, duplicate and invalid geography cases |
| 1: Upload-to-export workflow | County CSV wizard, audited join, comparison table and CSV/JSON/Markdown exports; then tract and XLSX support | One complete valid study works; invalid inputs block appropriately; every row accounted for; county data stays county-level |
| 2: Map workspace and services | Linked boundary map/table, detail panel, filters, multi-area comparison, site upload and audited HRSA layer | Map/table values agree; selections persist; legends, exclusions, periods and point locations are correct |
| 3: Planning brief and reproducibility | Source register, validation/join report, assumptions, receipt and settings restoration | Matching inputs/releases/settings reproduce results; settings-only files clearly require original inputs; brief labels synthetic data and limitations |
| 4: Documentation, usability and release | Worked tutorial, control guide, practitioner walkthrough, hosting/resource checks and regression verification | A new user completes the full task; session isolation, errors and resource limits tested; existing dashboard still works |
| 5: Portfolio and LinkedIn | Update case study; capture real screenshots; prepare 60–90 second demonstration and draft post | Claims match verified features; quantify only measured results; no private uploads in public assets |
| 6: Expansion | Additional sources, national geography, routing or private accounts as justified | Each addition passes data/method/usability gates and a cost review |

Phases 0–4 define the Arizona release. First finish a small end-to-end county study, then extend it to tracts and richer maps. Do not promise dates until the first implementation and performance measurements.

## Documentation delivered with the features

- Quick start and downloadable synthetic templates.
- Control reference explaining purpose, defaults, reset behavior, units and what changes.
- Upload mapping and validation examples, including unmatched geography and duplicate rows.
- Worked tutorial: choose county → inspect tract conditions → upload tract activity → review joins → add service sites → compare areas → export brief.
- Separate county example explaining why county totals cannot be converted to tract activity.
- Source catalog, methods/limitations, refresh instructions and technical reproduction guide.

Verify all tutorial numbers and screenshots against the completed app. Use plain-language error messages, accessible tables, readable colors and keyboard-operable controls.

## Architecture, cost and verification

Reuse Streamlit and Python initially. Evaluate map components against required interactions, accessibility, dependency compatibility and hosting limits before choosing. No new AWS infrastructure or application rewrite is required by this plan.

Test geographic IDs, duplicate/cardinality failures, zero versus missing, denominator compatibility, period/vintage mismatches, coordinates, malformed/oversized uploads, safe exports, stale state, cross-session isolation and receipt reproducibility. Measure load time, parsing time, peak memory and concurrent sessions on the target host. Confirm basemap attribution, use conditions and cost. Keep a rollback path to the validated dashboard.

Private/confidential use is a later architecture milestone requiring authentication, authorization, isolated storage, retention/deletion policies and reviewed logging. National acquisition is a separate pipeline milestone.

## Portfolio and employment value

Present evidence of public health reasoning, geographic data integration, evaluated descriptive ML, usable workflows and reproducible outputs. Differentiate from existing public dashboards through integration of user program data and documented planning briefs.

Update the existing case study after release verification; prepare an actual synthetic-data demonstration and LinkedIn draft. Distinguish implemented, tested and planned capabilities. Do not claim adoption or improved health outcomes without evidence. This planning update does not publish a post, change the live app or provision paid services.

## Immediate next task

Complete Phase 0: review the county workbench module, define county and tract upload templates, create synthetic fixtures with expected results, and sketch the upload-to-map-to-brief journey. Then build the county upload wizard as the first complete increment.

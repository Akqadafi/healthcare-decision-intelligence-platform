# Step 1 — study design and implementation handoff

Prepared October 27, 2026. Design and fixture package only; the live app is unchanged.

## The first user and task

A program analyst compares one month's outreach contacts across selected Arizona counties with one public measure. Uninsured rates or transportation barriers are intended choices after source mapping is verified. The executable fixture uses an invented generic need measure, not a government estimate.

The analyst leaves with a comparison table, a list of places to investigate, the join/validation report and a planning brief explaining sources and assumptions. Low recorded activity does not prove unmet need.

## Source review: reuse and gaps

| Component | Verified in source | Next action |
|---|---|---|
| workbench.py / Study | County scope, month, program and thresholds | Wrap in versioned UI study state; attach question, measure definition and source metadata |
| parse_contacts | Bounded UTF-8 CSV, exact canonical fields, scope checks, duplicate blocking, row errors and input checksum | Add confirmed column mapping before calling; do not silently discard or aggregate |
| compare_contacts | Sorted county results, contacts/1,000, threshold flags, missingness and join counts | Keep logic separate from widgets; use compatible population and measurement definitions |
| Context dates | Current contract uses observation_month | Upgrade to period start/end, period type and release metadata before integrating multi-year ACS estimates; never relabel a five-year estimate as one month |
| Existing county fixtures/tests | Four county contexts and three activity records; zero and missing differ | Reuse as arithmetic baseline; new files provide downloadable failure examples |
| Existing tract analysis | Geography audit, saved models and exploration | Reuse separately; current upload parser does not support tracts |
| Service sites | No upload contract implemented | Draft contract below; coordinate validation and spatial association come later |
| Interface and exports | No complete upload wizard or full workbench receipt | Build one county CSV-to-export path before extending formats |

The new roadmap supersedes the national-first wording in the older pilot specification. No production-code change is part of this design step.

## Files to use

In examples/workbench-pilot:
- templates/county_contacts.csv: blank canonical county header. Header-only files must be filled before upload.
- outreach_SYNTHETIC.csv: existing valid example, including an explicit zero.
- context_SYNTHETIC.csv: invented populations and need values for arithmetic checks.
- study_SYNTHETIC.json: design configuration, definitions and expected accounting; not yet an app import format.
- expected_results.csv: independently specified expected answers; blank result cells mean unavailable.
- invalid/: five intentionally invalid examples, with expected messages in expected_validation.json.
- templates/tract_contacts_DRAFT.csv and tract_contacts_SYNTHETIC_DRAFT.csv: future tract contract, not accepted by the current parser.
- templates/service_locations_DRAFT.csv and service_locations_SYNTHETIC_DRAFT.csv: future point-layer contract, not accepted by the current parser.

All activity counts and example site locations are invented. County and tract identifiers are real geographic identifiers. The two tract IDs appear in the saved boundary join; this does not independently verify model eligibility. Synthetic sites do not represent clinics and are not geocoded client addresses.

## Upload field contracts

County: county_fips (five-character registry ID), reporting_month (YYYY-MM), program (selected program), contacts (nonnegative integer). Unique key: county × month × program.

Tract draft: tract_geoid (eleven-character ID in the supported boundary registry), reporting_month, program, contacts. Unique key: tract × month × program. Validate membership and vintage, not just length. Never infer tract activity from county totals.

Site draft: site_id (unique text), site_name (public/non-sensitive description), site_type, latitude, longitude, as_of_date (ISO date). Require finite coordinates in valid ranges and review locations outside the selected study area. Sites are a separate layer; their positions cannot establish the residence or number of people served. Optional capacity is deferred until units are defined.

Treat identifiers as text when importing into Excel. Do not automatically pad malformed identifiers or invent missing ones. Initial CSV users supply exact headers; the later wizard proposes mappings for confirmation. XLSX follows the complete CSV workflow.

## Expected study result

Settings: January 2025; Demo outreach; need >=20%; activity <2 contacts per 1,000 residents.

| County | Need % (invented) | Contacts | Contacts / 1,000 | Interpretation |
|---|---:|---:|---:|---|
| Apache | 30 | 10 | 1.00 | Meets investigation thresholds |
| Cochise | 10 | 80 | 4.00 | Does not meet both thresholds |
| Coconino | 25 | 0 | 0.00 | Meets thresholds; explicitly reported zero |
| Maricopa | 22 | Unknown | Unknown | Unclassified; no uploaded record |

Three uploaded rows, three matched, zero rejected; one selected county with no activity record; three classifiable counties, two flags. A rate equal to 2 is not below 2. A need value equal to 20 meets the threshold. Do not call contact rates participation percentages or coverage of eligible people.

Invalid examples each block the entire upload:
- duplicate_county: row 3 duplicates row 2; do not sum.
- unknown_county: row 2 contains an unsupported county.
- missing_contacts: row 2 has no count; do not replace with zero.
- lost_leading_zero: row 2 identifier is malformed.
- wrong_period: row 2 differs from the selected month.

## Screen sketch

This is the intended layout, not a working upload interface.

```text
START STUDY
Question [................................................]
Geography [County v]  Areas [Apache, Cochise, Coconino, Maricopa]
Month [2025-01]  Program [Demo outreach]
Measure [Choose v]  [Definition, units, dates and source]
[Use synthetic example]                         [Continue]

ADD DATA
[Download template] [Choose CSV]
Preview rows -> Confirm column mapping
[Contacts may include repeats: counting-unit explanation]
Errors: row / column / reason / how to fix
[Replace file]                           [Review matches]

REVIEW
Uploaded 3 | Matched 3 | Invalid 0 | Areas without records 1
Public period [shown] | Activity month [shown]
Compatibility notes and required rationale if applicable
[Back]                                    [Explore]

EXPLORE
+------------------+------------------------+------------------+
| Measure / filters| Boundary map           | Selected area    |
| Need threshold   | Legend, units, period  | Need, contacts,  |
| Activity threshold| Missing-data category | rate, sources,   |
| Layers / sites   | Select communities     | limitations      |
+------------------+------------------------+------------------+
| Linked accessible table / selected-area comparison          |
+-------------------------------------------------------------+
[Clear selection] [Change upload] [Download table] [Prepare brief]

BRIEF
Question | selected areas | findings | unknowns | sources
Thresholds | units | periods | assumptions | limitations
[Results CSV] [Validation/join report] [Receipt JSON] [Brief MD]
```

Controls: thresholds change investigation flags; map/table filters change the displayed scope and must be recorded in export settings. Site toggles only change visibility. Changing uploads or mappings clears stale results. Map selections do not refit tract models. Reset clears uploaded state. Invalid uploads cannot reach Explore.

The first county increment can use a table before the linked map arrives. Label unavailable future actions rather than displaying functioning-looking controls.

## Study state and receipt design

State: schema version, question, geography type/IDs/vintage, activity period, program, count definition, selected public variable and population universe, source periods/releases, mappings, thresholds, display scope and selected areas.

Receipt: state plus source/input hashes, validation and join totals, transformations, compatibility decisions, app revision, timestamp and result hash. Retain only the public/synthetic data needed for this demo. A checksum identifies bytes, not data accuracy. Settings alone do not restore missing input files.

Do not log uploads or share them through global caches. Verify session isolation and clear behavior in implementation. Uploads reach the hosting server; the public demo is not for confidential data.

## Reproduction and next implementation

Run from the repository with its Python environment:

```powershell
.\.venv\Scripts\python.exe scripts/verify_workbench_design.py
.\.venv\Scripts\python.exe -m pytest tests/test_workbench.py tests/test_scoring.py -q --no-cov
```

Verification on October 27: the design verifier passed all four county expectations and five invalid examples. The existing workbench and scoring suites passed all 52 tests. Ruff passed for the new verification script. Pytest emitted a cache-directory warning; the tests completed successfully. No browser or deployment verification was required for this documentation/fixture increment.

Next: connect Study and parse_contacts to a county CSV wizard, add a public-data period/metadata adapter, then comparison and safe CSV/JSON/Markdown exports. Use these fixtures as the acceptance contract. Tracts, XLSX and HRSA site layers follow; no new hosting or deployment is needed now.

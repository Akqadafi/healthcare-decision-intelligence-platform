# Arizona research workflow: first build specification

Prepared October 21, 2026. Updated after the first code increment: pure CSV validation and comparison functions are built and tested. The upload interface, source catalog, exports, and complete study receipt are not built.

This narrows the October 14 Workbench plan into an Arizona pilot. It does not replace the larger national roadmap. CSV is the first build increment; XLSX follows once the CSV journey passes its checks. The existing Arizona dashboard remains available with its current scoring.

## Study question

Which selected Arizona counties have a relatively high value on a chosen public need measure and low recorded outreach activity during a specified reporting period?

The pilot compares one program and one month. Use contacts as the counting unit. A contact can be repeated for the same person, so the output is contacts per 1,000 residents, never percent of people served. Low recorded activity is a reason to investigate, not proof of unmet need or poor program performance.

## A complete user journey

1. Start a study: enter a question, select counties, choose one reporting month and one program. The prototype accepts public or synthetic aggregate data only.
2. Select one measure: display its definition, units, source, observation period, and population universe. The original weighted planning score is not the default research measure.
3. Upload a CSV: map county FIPS, reporting month, program, and contact count; confirm that counts mean contacts. Show a preview before joining.
4. Review checks: report invalid rows and duplicate keys with row numbers. Block analysis until errors are corrected; do not discard rows silently.
5. Review compatibility: show the public observation period and service month separately. Different periods require a recorded explanation before descriptive comparison. Incompatible geography blocks analysis. Population-normalized activity requires a compatible population denominator; it is not an eligibility-based coverage rate.
6. Explore results: show need measure, contacts, denominator, contacts per 1,000 residents, and data status. Let the researcher set visible investigation thresholds. Preserve all selected counties, including those with no uploaded service record.
7. Export: download the results CSV, validation/join report, study receipt JSON, and a short Markdown report. Separate downloads are sufficient for the first increment; ZIP restore and a standalone reproduction recipe follow later.

## Input contract

CSV: UTF-8, comma-separated, one header row, at most 10 MiB and 100,000 data rows. These are proposed caps, not a measured capacity claim. Reject malformed input, unsupported fields, or ambiguous mappings with a useful message. Preserve FIPS as strings.

| Field | Rule |
|---|---|
| county_fips | Five-digit Arizona county code from the supported registry; keep leading zero |
| reporting_month | YYYY-MM and equal to the study month in this first increment |
| program | Nonempty name matching the selected program |
| contacts | Nonnegative integer written as 1–15 ASCII digits; zero is valid; blank is an error. Larger counts are rejected explicitly to bound arithmetic |

The row key is county × month × program. Duplicate keys block the study. The pilot does not infer whether rows are additive or deduplicate people. Out-of-scope counties also block until scope or input is corrected. Missing county rows mean unknown service activity, not zero contacts.

## Outputs and calculation

`contacts_per_1000 = contacts / resident_population * 1000`

Use unrounded values for threshold decisions and display rates to two decimal places. A missing, zero, or invalid denominator prevents rate calculation for that county; label it and omit its investigation classification. Report counts of classifiable and unclassifiable counties.

Use an inclusive need threshold and a strict low-activity threshold, both visible in the UI. A county is flagged when `need_percent >= need_threshold` and `contacts_per_1000 < activity_threshold`. Unknown activity is not classified as low.

Every uploaded row must appear in the validation/join accounting. With valid unique inputs, matched + rejected/unmatched rows equals uploaded rows. Public-only selected counties are reported separately; they are not extra uploaded records.

Receipt: schema version, study question, geography scope, month, program, counting definition, source release/observation metadata, file hashes, confirmed mappings, join counts, denominator definition, thresholds, recorded compatibility decisions, application commit, execution time, and result hash. A hash identifies file bytes; it does not certify source accuracy.

The report must state whether the example is synthetic, the measurement periods, missing counties, and the limits of interpretation. Do not infer causes or recommend funding cuts from this comparison.

## Worked example

See `examples/workbench-pilot/`. County codes and names identify real Arizona counties; every numeric measure and service count is invented for software testing. These are not government estimates or real outreach results.

Fixture period: January 2025 for both synthetic context and service records. Program: Demo outreach. Need threshold: 20%; low-activity threshold: 2 contacts per 1,000 residents.

| County | Synthetic need % | Synthetic residents | Contacts | Per 1,000 | Expected result |
|---|---:|---:|---:|---:|---|
| Apache | 30 | 10000 | 10 | 1.00 | Investigate |
| Cochise | 10 | 20000 | 80 | 4.00 | Outside chosen thresholds |
| Coconino | 25 | 10000 | 0 | 0.00 | Investigate; explicit zero |
| Maricopa | 22 | 50000 | unknown | unknown | Unclassified; no uploaded record |

Expected accounting: three uploaded records, three matches, no rejected rows, one selected county without a service record, three classifiable counties, and two flags. The synthetic fixture establishes arithmetic and missingness behavior only. Before using government measures, verify exact variable definitions and source periods rather than substituting these fixture labels.

## Acceptance cases for the first build

- Valid fixture produces the worked example exactly.
- An explicit zero remains zero; an absent county remains unknown.
- Duplicate Apache rows block analysis without summation.
- Unknown FIPS, negative contacts, decimal contacts, blank counts, or a different month produce row-level errors.
- A period mismatch blocks continuation until the researcher records the allowed descriptive-comparison rationale; the exported report retains it.
- A zero population yields no rate or flag, with a visible reason.
- A rate exactly 2 is not low; a need value exactly 20 meets the need threshold.
- Changing thresholds recalculates results and updates the receipt.
- Exported values and join counts match the screen. Neutralize spreadsheet formulas in exported text; never execute uploaded content.
- The existing Arizona snapshot result and dashboard behavior remain unchanged. Resolve the known local Streamlit test-startup problem or obtain a passing supported-environment run before claiming dashboard regression checks pass.

## Build order

First add pure parsing/validation and analysis functions with the fixtures. Then add the study object and guided CSV screens. Complete export and an end-to-end walkthrough before extending to XLSX. Keep a versioned example receipt and expected results alongside tests.

No new AWS deployment is needed. National acquisition, private accounts, confidential data, statistical prediction, and study-package import are outside this first increment.

## Portfolio and LinkedIn use

The current rollback post describes completed work and can proceed through its existing review process. Any Workbench preview must say it is being designed or built. A completed-study post waits until the upload-to-export journey passes the acceptance cases. Use the sample report and an actual walkthrough as its evidence.

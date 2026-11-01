# Compare outreach across communities

Updated October 27, 2026 — simplified local pilot.

## Start here

Choose **Outreach workbench** in the dashboard menu. Then choose:
- **Try an example**: opens explained results immediately, with invented data.
- **Use my spreadsheet**: connects your county outreach counts with public indicators.

The two paths stay separate. The example never uses your uploaded records.

## Try the example

Four counties show why zero and missing are different. Apache has 1 contact per 1,000 residents, Cochise has 4, Coconino explicitly reported zero, and Maricopa supplied no record. None of these counts describe real activity.

Read the short explanation, chart and table. **Highlight counties using my criteria** is optional and off initially. Turning it on reveals two thresholds; their starting values are illustrative, not recommendations. Turning it off removes highlighting from both the display and the exported report.

## Use your spreadsheet

1. Download **Get a starter CSV** if needed.
2. Include County, Month, Program and Contacts. Standard technical headers also work.
3. Use Arizona county names (Apache or Apache County) or five-digit codes. No fuzzy matches are made.
4. Upload a CSV (UTF-8). The app recognizes common headers; expand **Check spreadsheet columns** if you need to change the mapping.
5. Use one month and program per file. The app reads these from your rows rather than asking you to type them again.
6. Choose uninsured adults, transportation barriers or poverty as community context.
7. All Arizona counties are included initially. Expand **Which counties should appear?** to change scope. Uploaded rows outside that scope must be corrected; none are silently dropped.
8. Review the source dates and acknowledge that historical indicators are background, not a trend.
9. Select **Show my comparison**.

Files must contain non-sensitive aggregate data only. They reach the hosting server. Do not include patient records, names or home addresses. This pilot does not save uploads to disk or a shared cache.

Limits: 10 MiB, 100,000 data rows, 100 uniquely named columns. Excel files must first be saved as CSV. Duplicates, unknown counties, blank/negative counts and malformed rows block comparison with an explanation. Zero is a reported zero; missing records are unknown.

## Understand the results

- **Counties compared**: the selected geographic scope.
- **With activity records**: counties with a validated uploaded row.
- **No activity record**: selected counties without records; they remain visible in the table.
- **Contacts per 1,000 residents**: counts divided by resident population, multiplied by 1,000. Repeat contacts may be included.
- **Record status**: distinguishes a supplied count, reported zero and missing record.

The chart omits counties without activity records. Rates are not percentages of eligible people served. Low activity does not establish unmet need, program failure or intervention effectiveness.

Expand **Sources, dates and how to interpret this** for definitions and dates. ACS poverty covers 2020–2024; CDC context uses the bundled manifest's 2022–2023 BRFSS range and 2023 population. These are not monthly estimates. County uncertainty intervals are unavailable in the source table.

## Save or change your work

**Download comparison report** provides one ZIP containing a readable Markdown brief, results CSV, source/processing receipt and join report. Technical details remain available in an expandable section.

**Back to my spreadsheet** lets you revise the upload before running a new comparison. **Start over** clears the study and renews the upload input. Download your report before leaving; this pilot has no saved accounts or study restoration.

Results reflect a snapshot of confirmed input and settings. Keep original files and source releases for reproduction. Dataset/model versions are separate from application releases.

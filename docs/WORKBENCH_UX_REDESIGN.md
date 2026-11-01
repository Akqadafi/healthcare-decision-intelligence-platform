# Workbench UX revision — October 27, 2026

Status: local, unreleased. See CHANGELOG.md. No dataset, saved model, public deployment or application release version was changed.

## Design decisions

- Begin with the user's task: try an example or compare an uploaded spreadsheet.
- Separate the invented demonstration from real public context so users cannot accidentally mix modes.
- Show only the current step. The example skips spreadsheet setup.
- Recognize standard headers, county names, period and program; ask only for missing mappings.
- Keep technical names, geographic scope and source details behind expandable sections.
- Use county names, descriptive column labels, a rate chart and factual missing-record summaries.
- Explain zero versus missing where the results appear.
- Make threshold highlighting optional and off by default. Do not export hidden flags or active thresholds when it is off.
- Provide one report download with readable brief, CSV and provenance.
- Use visible labels, native keyboard-operable controls, table alternatives and inline error recovery.

## Verification

The full 103-test regression suite passed after the redesign, along with lint. A pre-existing pytest cache-directory warning did not affect assertions. Targeted tests cover the guided example, reset, optional highlighting, disabled-highlight exports, exact county-name resolution, and unknown county handling.

Browser inspection confirmed the task-selection layout, explained example results, chart, table, optional toggle and streamlined upload screen. Screenshot: Applications/workbench-simplified.png. Browser file-chooser automation did not complete the new upload journey; the spreadsheet path is additionally exercised by Streamlit AppTest with a simulated uploaded file, not represented as a real browser upload.

## Remaining scope

This is still the county CSV pilot. XLSX, tract uploads, service-site layers, persistent studies, public-host load testing and deployment remain separate tasks. User testing with a public health practitioner is still needed; automated checks do not establish usability for that audience.

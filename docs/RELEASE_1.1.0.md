# Version 1.1.0 release record

Prepared November 1, 2026. This release adds the county CSV outreach workflow,
guided Apache tract example, clustering explanations and optional indicator filtering.
The sidebar identifies version 1.1.0. Public datasets and fitted models are unchanged.

## Verification

- Full local pytest suite: 105 passed (86% source coverage).
- Ruff: passed. Git diff whitespace check: passed.
- Six-page dashboard verification: passed; 15 counties and Apache score 75.1 retained.
- Synthetic workbench fixtures: four county results and five invalid-upload cases passed.
- Public-data pipeline: rebuilt 15 county records successfully.
- Non-blocking local warnings: pytest cache directory unavailable; Streamlit automatically
  coerced mixed tract-comparison column types for Arrow rendering.
- GitHub CI and public deployment verification: pending at release preparation.

## Scope and recovery

County CSV uploads only; tract and service-location templates remain design drafts.
Uploads must contain public/non-sensitive aggregate records. They reach the server;
application upload state is session-scoped and is not written to permanent storage.

Deployment target is the existing Streamlit Community Cloud app tracking main.
If release verification fails, revert the release merge through Git and verify the
previous dashboard returns. No AWS deployment is part of this release.

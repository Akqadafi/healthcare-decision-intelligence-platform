# Current project status

Reviewed October 18, 2026, against local source commit `ae378ff0bff13ca2ab6c74f065927766cfcbdd70`, saved AWS evidence, and the proposed Workbench plan. Documentation changes from this review are local and uncommitted. This is an engineering inventory, not an independent audit.

## What exists

October 25 deployment target confirmed by the owner:
https://healthcare-decision-intelligence-platform-2hnrmnekvpybfu25eapp.streamlit.app/.
The address returned HTTP 200 with Streamlit HTML. Public UI behavior and management
settings have not yet been verified; local tract changes have not been published.
Use this existing app for the release rather than creating another deployment.

October 24 dashboard integration: the original Streamlit app now has an **Explore
census tracts** page with saved-model method/group-count selection, county/group/measure
filters, range and missingness controls, two-tract uncertainty comparison, statewide
profiles, evaluation tables, filtered CSV downloads, and a matching study receipt.
Selections persist across page navigation. The guide and Apache walkthrough are
available in Downloads & help. The full **91-test suite passes**, including all county
and tract dashboard tests, when executed outside the filesystem/network sandbox.
The prior Windows socket startup limitation did not recur in that environment.
Docker packaging includes the saved study and documentation; the local image build
remains unverified because the Docker Desktop Linux engine is not running. No public
deployment, push, or cloud action was performed.

Browser verification in Edge passed the Apache tutorial flow, model switching, and
CSV/receipt downloads with matching checksums. The filtered export contains 18 rows;
screenshots were visually checked. Evidence: `docs/evidence/tract-dashboard/`.
Downloads avoid unnecessary app reruns. The verified automated flow took 43.8 seconds.

October 21 code increment: `src/healthcare_di/workbench.py` now provides bounded UTF-8 CSV parsing, row-level validation, a minimal study configuration, and county comparisons. The synthetic demo is runnable with `python scripts/workbench_demo.py`. It preserves unknown activity, enforces duplicate/scope checks, records period-review rationale, and returns join/classification counts. This does not include an upload screen, CSV column mapping UI, public measure catalog, exports, or a complete research receipt.

Verification for this increment: 76 tests passed (37 new cases plus the existing 39 non-dashboard tests); new module coverage 98%, combined package coverage 88%. Streamlit dashboard tests were excluded because of the previously recorded local startup stall. New-file lint passed. No cloud resources were created and no changes were pushed or published.

| Capability | Status | Evidence and limits |
|---|---|---|
| Arizona data pipeline | Built; rerun locally October 18 | `src/healthcare_di/pipeline.py`; 15 rows produced from bundled CDC, Census, and CMS snapshots |
| Source and output checks | Built; output checks passed October 18 | `contracts.py`, `quality.py`; all 18 checks in the new output quality report passed |
| Weighted county scores and explanations | Built; snapshot result reproduced | `scoring.py`; Apache ranks first at 75.1. Weights and suggested actions are assumptions, not validated effects of spending |
| Streamlit county views and budget scenarios | Built | `dashboard/app.py`; current source includes county selection, allocation controls, and missing-rating comparisons |
| Build receipt | Built | Manifest records output hash, mode, row count, and build time. It is not a complete provenance record for every source |
| API refresh | Code exists | `ingestion.py`; not rerun during this review. Snapshot checks do not establish current API availability |
| Tests and CI | Present | Python tests plus Terraform/container/browser jobs in `.github/workflows/ci.yml`; distinguish configured checks from a passing run |
| AWS deployment and rollback | Historical demonstration completed October 11 | `docs/evidence/aws-rollback-summary.json`; temporary ECS/Fargate environment, same image with failing health command, revisions 2 → 3 → 2, health `200/ok` |
| AWS cleanup | Historical checks passed | Saved record: 30 resources created and destroyed; API absence checks passed. No fresh AWS account or billing inspection during this review |
| PostgreSQL and dbt | Scaffolding only | Dashboard serves validated CSV outputs; no exercised warehouse pipeline |
| Research Workbench | Partial core functions as of October 21 | `workbench.py` and synthetic CLI demo; no researcher upload interface, national study catalog, or study export workflow |

## AWS claims to preserve

- The failed candidate reused the baseline image and changed the container health command. This does not test arbitrary code defects or all outage types.
- Detection took 779.443 seconds from deployment creation to failure publication.
- The failure and rollback-completion publications were 36 seconds apart. That is not measured downtime or a general recovery guarantee.
- Final verification came later after a log-pagination repair. The saved record includes failed verifier attempts and corrections.
- The demonstration used local AWS credentials. GitHub OIDC token exchange remains untested.
- The public Streamlit deployment and historical AWS demonstration are separate. Do not describe the public app as currently hosted on AWS based on this test.
- A future public AWS service still needs the documented HTTPS and alarm work.

## Review artifacts

The fresh snapshot build is saved outside the repository to avoid replacing bundled outputs:

`C:/Users/Semio/OneDrive/Documents/ChatGPT/Applications/status-audit-2026-10-18/data/`

It contains the county CSV, quality report, and build manifest. The rerun reproduced 15 counties and Apache's 75.1 score.

### Verification on October 18

- Project tests excluding `tests/test_dashboard.py`: **39 passed**, 84% measured package coverage. A pytest cache-write warning did not fail the run.
- Full-suite attempt did not complete. After an initial error and stalled run, a rerun with workspace temporary storage passed the contract tests but stalled while Streamlit initialized an asyncio event loop. The 45-second diagnostic stack showed Windows `socket.accept` inside `_fallback_socketpair`, before dashboard assertions. Both stalled processes were stopped. This does not establish a dashboard logic defect, and the three dashboard tests remain unverified today.
- Portfolio website build: passed, including static export. Existing rendered-content tests: **3 passed**.
- Documentation and portfolio diffs: whitespace checks passed.
- No fresh AWS deployment, Terraform validation, Docker build, API refresh, or public browser walkthrough was performed. Older successful CI/browser results are historical, not a substitute for today's incomplete full-suite run.

## Public material reconciliation

- README: corrected the outdated future-tense recovery-test roadmap entry and linked this status record.
- Repository case study and project card: added Census, historical recovery evidence, and the boundary between the dashboard and planned Workbench. Removed claims that rankings establish the best investment.
- Portfolio website source: corrected editable-reach wording, added the recovery demonstration, and marked warehouse and Workbench work as incomplete.
- LinkedIn draft in Applications: reviewed against the saved evidence. Its same-image health-check failure account remains accurate; it claims no Workbench features or downtime result.
- Website publication, public link access, and GitHub CI were not reverified by this local review. Local wording changes are not yet reflected on the public website or GitHub.

## Next work

October 24 modeling milestone: official 2023 polygons match all 1,765 tract IDs.
Five-feature clustering uses 1,730 tracts, with 35 exclusions retained. Ten K-means
and Ward candidates were compared across k=2–6, with 20 subsamples per candidate,
feature removal, income replacement, alternative scaling, county omission, and
K-means initialization checks. Only two-group K-means passed the prespecified
project heuristics. See [model report](TRACT_MODEL_REPORT.md) and the saved interactive
analysis under `docs/evidence/tract-study/models/`. This is descriptive analysis,
not a clinical or funding model. All 86 non-dashboard tests pass. The dashboard
integration, guide, and worked tutorial remain next; no publication has occurred.

October 24 acquisition milestone: `scripts/tract_data_audit.py` now downloads and
caches official PLACES 2025 and ACS 2019–2023 sources, preserves uncertainty/status
fields, audits the full tract join, and writes hashes and exploratory outputs.
There are 1,765 ACS tracts, 1,740 matched PLACES tracts, 25 ACS-only tracts, and
1,725 complete rows across six candidate features. See [the audit](TRACT_DATA_AUDIT.md)
and `docs/evidence/tract-study/`. Four new tests and all 80 non-dashboard tests pass;
lint passes. No clustering or tract dashboard is implemented yet. Next: boundary
verification, feature/uncertainty review, then evaluated clustering.

October 24 direction update: prioritize the [Arizona tract analysis and dashboard plan](TRACT_ANALYSIS_PLAN.md). Begin with verified ACS/PLACES releases and compatible tract geography, then exploratory analysis and evaluated clustering. A screen-by-screen user guide and worked tutorial are release requirements. The county upload functions remain available; the guided county upload UI is deferred while this data-science study takes priority. No tract features or ML results are claimed yet.

October 21 follow-up: [the Arizona pilot specification](ARIZONA_PILOT_SPEC.md) and `examples/workbench-pilot/` synthetic fixtures now define the first CSV study and its expected results. These are planning artifacts, not working Workbench features. The source commit remains `ae378ff`; no new application behavior was added. The October 18 test results above retain their original date.

Write the first Arizona study specification using synthetic outreach counts. Define acceptable geography and periods, the participation denominator, rejected-input behavior, and the exported study report before adding the upload interface. Keep the existing Arizona dashboard as a separate view.

# Publish the integrated dashboard on Community Cloud

Prepared October 25, 2026. This runbook does not confirm publication.

Existing public app supplied by the owner:
https://healthcare-decision-intelligence-platform-2hnrmnekvpybfu25eapp.streamlit.app/

An HTTP check on October 25 returned 200 and Streamlit HTML. This confirms the
address responds, not that the app is awake, its controls work, or its deployment
settings match those below. Update this existing app; do not create a duplicate.

## Deployment settings

| Setting | Value |
|---|---|
| Repository | `Akqadafi/healthcare-decision-intelligence-platform` |
| Production branch | `main`, after the reviewed release is merged |
| Entrypoint | `dashboard/app.py` |
| Python | 3.12, matching the project's Linux runtime configuration |
| Dependencies | Root `requirements.txt`, which uses `constraints-runtime.txt` and the local package |
| Secrets | None required for the bundled snapshot dashboard |
| App URL | Retain the existing public URL above |

Serving uses saved results; training and Census/CDC refreshes are separate local jobs.
Do not add the Census key or AWS credentials to the app just to serve these snapshots.
Docker and Terraform are not needed for this hosting route.

## Release sequence

1. Review the accumulated changes, including the county Workbench core and tract study.
   Keep raw national downloads, virtual environments, credentials, Terraform state,
   and saved infrastructure plans out of Git. Include the saved tract CSV/JSON/GeoJSON
   files, dashboard assets, guide, tutorial, and evidence screenshots.
2. Commit on a release branch and open a pull request. Require the Python and container
   checks to finish; inspect failures before merging. The full local suite last passed
   91 tests; later control-help edits passed their two targeted tests. These are local
   results, not confirmation of a hosted CI run.
3. In the Streamlit workspace, open the existing app at the URL above. Confirm its
   repository, branch, entrypoint, and Python version against the intended settings.
   The public HTTP response does not expose or verify those management settings.
4. Merge the reviewed release into the configured branch. An existing app connected
   to that branch may update automatically. For a new app, deploy after setting the
   repository, branch, entrypoint, and Python version.
5. Watch build/startup logs. Test the public app in a signed-out browser: all five
   pages, county score 75.1 for Apache, tract count 1,765, Apache tract filter 18,
   model-change warning, and both CSV/receipt downloads. Follow the worked tutorial.
6. Record the actual public URL and deployed commit in CURRENT_STATUS. Update portfolio
   links only after those public checks pass. If a release fails, restore the previous
   reviewed revision or revert the release and verify the recovered app.

Local preflight evidence: `docs/evidence/streamlit-release-preflight.json`.
The hosted environment still needs dependency, memory, and responsiveness checks.

Official instructions:
[Deploy on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

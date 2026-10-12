# Historical AWS demonstration evidence

The sanitized [result summary](aws-rollback-summary.json) includes selected fields
and event timestamps exported from the October 11, 2026 AWS demonstration.
The [recovered dashboard screenshot](aws-dashboard-recovered.png) records the
application after rollback. These artifacts document a historical test; they do
not imply the current Streamlit deployment runs on AWS.

Release A (revision 2) completed. B (revision 3) reused the exact same image but
changed its container health command to fail. ECS recorded deployment failure,
rolled back to A, and reported healthy application/ALB checks. All 30 Terraform
resources were destroyed; API absence checks passed.

The 36-second interval is between published failure and completed-rollback events.
It is not downtime or a general recovery-time guarantee. Detection took about
13 minutes from deployment creation. Final verification was delayed by fixing
log pagination. The summary retains the failed verifier attempts and corrections.

Local AWS CLI credentials were used. GitHub OIDC remains untested. Raw logs and
identifiers remain local. This curated evidence is not independent attestation;
the runbook explains how to reproduce the experiment in a dedicated environment.

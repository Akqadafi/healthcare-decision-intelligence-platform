# Community Health Operations Intelligence

Status reviewed October 18, 2026. See [current status](../docs/CURRENT_STATUS.md) for evidence and limits.

## The question

How can a public-health team compare community conditions across Arizona counties and examine a possible outreach budget?

## Current application

The Python pipeline combines public CDC, Census, and CMS snapshots for Arizona's 15 counties. It checks source fields and county identifiers, calculates a weighted planning score, and writes a county table with a quality report and build manifest.

The Streamlit dashboard shows county profiles, score explanations, and a budget scenario. It also compares rankings under different assumptions about missing hospital ratings. The score and suggested actions are planning assumptions that need review with local experts. They do not establish where spending will produce the greatest benefit.

The dashboard reads validated CSV outputs. PostgreSQL and dbt files are scaffolding; they are not an exercised warehouse pipeline. API refresh code exists, but the repeatable demonstration uses bundled snapshots.

## AWS recovery demonstration

On October 11, a temporary ECS/Fargate environment hosted the application. A new task revision reused the working image but changed its container health check to fail. Saved evidence records a failed deployment and recovery from revision 3 to revision 2, followed by healthy application checks.

The verification scripts also needed repairs: one rejected newer AWS response fields, and another failed to paginate application logs. The evidence preserves those failures and corrections. Cleanup records show 30 Terraform resources removed and API absence checks passing.

This was one controlled health-check failure. The 36-second interval between published failure and rollback-completion events is not downtime or a recovery guarantee. Detection took about 13 minutes. Local AWS credentials were used; GitHub OIDC was not exercised. The current public Streamlit deployment is separate from this historical AWS test.

[Saved AWS evidence](../docs/evidence/README.md)

## Proposed next release

The Public Health Research Workbench would support researcher-supplied aggregate files, measure selection, and study exports. Those features are planned. The current dashboard has no researcher upload workflow or national study catalog.

## Interview explanation

“My background is in public-health analysis and research. This project brings county data into a repeatable pipeline, checks it, and makes the scoring assumptions visible in a dashboard. I also tested a failed deployment in AWS and recorded the recovery. The research workbench is the next proposed stage; the working application currently covers Arizona.”

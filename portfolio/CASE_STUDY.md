# Portfolio case study: Community Health Operations Intelligence

## The challenge

Health systems and public-health teams often have abundant data but no consistent answer to a
practical question: where should the next outreach dollar go? Data arrives from different agencies,
uses different geography fields, carries different update cycles, and rarely ends in an action.

## What I built

I built an end-to-end decision intelligence product for Arizona's 15 counties. It retrieves and
normalizes public CDC and CMS data, computes a transparent four-domain priority index, explains
the strongest drivers, and presents recommendations in an executive Streamlit application. A
resource simulator turns a budget and operating limit into a ranked deployment scenario.

## Engineering highlights

- Designed API ingestion with reproducible snapshot fallback for reliable demonstrations.
- Resolved county geography and missing-quality-data semantics explicitly.
- Created testable, deterministic scoring instead of fitting an unjustified model to 15 records.
- Added contracts, lineage, an ADR, model card, automated data-quality evidence, and CI.
- Containerized the product and authored safe-by-default Terraform for S3, KMS, and CloudWatch.
- Prevented accidental AWS spend by requiring an explicit deployment opt-in; CI never applies IaC.

## Outcome

The platform produces an action and an explanation for every Arizona county, validates all 15
records in CI, and demonstrates a credible bridge across healthcare analytics, data engineering,
DevOps, cloud governance, and executive communication.

## Résumé bullets

- Built a healthcare decision intelligence platform integrating CDC PLACES and CMS hospital data
  to rank 15 Arizona counties by health burden, social need, access, and provider-quality gaps.
- Developed an explainable scoring and resource-allocation engine with automated data contracts,
  lineage, quality controls, model governance, and explicit missing-data handling.
- Containerized a Streamlit executive dashboard and implemented GitHub Actions plus Terraform for
  a KMS-encrypted, versioned AWS data-lake foundation and CloudWatch observability.

## 30-second interview explanation

“I wanted the project to end with a decision, not just a chart. I combined public CDC and CMS data,
normalized it at county level, and chose an explainable weighted index because there are only 15
Arizona observations and no defensible outcome label for supervised learning. The app shows where
to invest first, why, and what a fixed budget can cover. I also treated reliability and governance
as product features: snapshots, contracts, tests, lineage, missing-data disclosure, Docker, CI,
and safe Terraform are all part of the repository.”

# AWS hosting, release, and recovery demonstration

## Current status and approval boundaries

Infrastructure and workflows are implemented locally. On 2026-10-11, all 28 bootstrap resources were created, checked, and destroyed. AWS API cleanup checks confirmed the demo resources and log groups were removed. A separate temporary dashboard test on 2026-10-11 deployed a verified image to Fargate, checked all four pages and interactive controls, injected a failing container health check, and confirmed automatic recovery to the exact completed baseline revision. Failure publication occurred 779.4 seconds after the ECS deployment's createdAt timestamp; rollback completion was published 36.0 seconds after the failure event. Read-only verification completed later after repairing CloudWatch log pagination; the original monitor was superseded without reinjecting a fault. All 30 resources and test images/log groups were then destroyed, with independent AWS API cleanup checks. Evidence is in evidence/dashboard-live-test-2/final-result.json. This test used local AWS credentials; GitHub OIDC workflow authentication remains untested. Evidence is stored locally in evidence/bootstrap-live-test/final-result.json. Review the saved bootstrap plan and cost before applying. The optional S3/KMS foundation remains disabled. Local dashboard deployment is covered in DEPLOYMENT.md.

The hosting environment is healthcare-di-dev in account 233781468925, us-west-2. Two public subnets host the ALB and Fargate tasks. Task ingress on port 8501 is restricted to the ALB security group. Outbound TLS permits image pulls and log delivery. This demonstration avoids a NAT gateway; tasks have public IP addresses. A production design may require private tasks, endpoints, stronger network controls, and HTTPS.

The reviewed bootstrap has no client ingress: allowed_client_cidrs=[] and container_image=null. It creates ECR, networking, ALB, logging, events, and IAM before an image exists. It does not create the ECS task/service until a validated image digest is supplied. Review client access separately before enabling it. GitHub-hosted runners need a reachable endpoint; use a reviewed public demo endpoint or a runner on an allowed network. For HTTPS, provide a valid ACM certificate and dashboard_hostname, then configure DNS to the alb_dns_name output.

## Bootstrap and initial release A

1. Run the Python/data/container checks and Terraform validation. Review evidence/plan-review/bootstrap.txt and COST_REVIEW.md. Copy infra/terraform/dev.tfvars.example to ignored dev.tfvars and keep account, region, access, and cost decisions explicit.
2. Generate and review a saved plan with the chosen tfvars. Only after approval, apply that exact saved plan. Do not apply a placeholder-image preview plan.
3. Read `terraform -chdir=infra/terraform output -json hosting`. Configure GitHub environment variables below. Push reviewed changes to main; run Reviewed AWS release with operation=publish. CI builds and validates the image before publishing an immutable source-commit tag. Download the image artifact and record its repository@sha256 digest.
4. Set container_image to that exact digest and allowed_client_cidrs to the reviewed access policy. Generate a second plan. Review the ECS task/service and any network access changes before applying that saved plan. Terraform never runs apply in CI.
5. Wait for initial deployment completion, then run the verification command below and the browser smoke test. Save the output alongside the passing CI run and validated-data.json. This establishes release A before testing recovery.

PowerShell plan commands (quote native Terraform arguments):

```powershell
terraform '-chdir=infra/terraform' plan '-var-file=dev.tfvars' '-out=approved.tfplan'
# After review and approval only:
terraform '-chdir=infra/terraform' apply 'approved.tfplan'
```

Baseline verification, using actual Terraform outputs:

```powershell
$hosting = terraform '-chdir=infra/terraform' output -json hosting | ConvertFrom-Json
$env:AWS_REGION = $hosting.region
.\.venv\Scripts\python.exe scripts/aws_release.py verify --account $hosting.account_id --cluster $hosting.cluster --service $hosting.service --target-group $hosting.target_group_arn --event-log $hosting.deployment_log_group --application-log $hosting.application_log_group --url $hosting.dashboard_url --evidence evidence/baseline
```

Run `scripts/cloud_dashboard_smoke.py --url URL --evidence evidence/baseline` with Playwright and Chromium installed to capture the dashboard and check all four pages. Record all 15 counties, Apache score 75.1, and the validated image's dataset hash. The endpoint must be reachable from the checking machine.

## GitHub OIDC and review gates

The dev-build and dev environments are configured and verified as restricted to main. The dev environment requires approval from Akqadafi; self-review is allowed so the repository owner can approve a manually initiated demonstration. Review the image digest shown by the publish job before approving deploy. OIDC subjects are restricted to the exact repository and environment, with sts.amazonaws.com as the audience. Publishing and deploying have separate IAM roles; no long-lived AWS key is stored in GitHub. Verify these environment protections before running workflows.

Both environments: AWS_ACCOUNT_ID, AWS_REGION.
dev-build: AWS_PUBLISH_ROLE_ARN, ECR_REPOSITORY_URL, ECR_REPOSITORY_NAME.
dev: AWS_DEPLOY_ROLE_ARN, ECS_CLUSTER, ECS_SERVICE, TARGET_GROUP_ARN, APPLICATION_LOG_GROUP, DEPLOYMENT_LOG_GROUP, DASHBOARD_URL.

Use the corresponding hosting outputs. Do not configure invented ARNs. The workflow is manually dispatched on main. operation=publish supports initial bootstrap; operation=deploy requires a healthy, completed existing release. The deployment job must be approved through the protected dev environment.

## Controlled failure B

Run Controlled dev rollback test only after release A meets every baseline check. Confirm healthcare-di-dev in the workflow input and approve the dev job. The script also checks the account, service name, Environment=dev tag, and enabled circuit breaker/rollback.

B uses A's exact image and changes only the ECS container health-check command to fail. The ALB and release A definition remain unchanged. The task definition explicitly defines health checks; ECS does not inherit Dockerfile health checks automatically. EventBridge preserves ECS deployment events in CloudWatch.

Success requires a failure event for B, a rollback event, A's exact task revision and image digest running, a COMPLETED deployment, healthy targets/tasks, a passing health endpoint, and application logs. The recovered dashboard browser test checks the expected county count and score. A normal deploy that rolls back fails verification rather than claiming a successful new release.

Evidence includes summary.json, timeline.jsonl, before/registered/submitted/latest/verified snapshots, failed-deployment-event.json, rollback-event.json, stopped-task details, screenshots, and browser checks. Detection time is submission to the server's failure event; recovery time is that event to confirmed healthy A. Polling and event delivery affect timing precision. The test measures recovery from a failed rollout, not every possible outage or data-loss scenario.

## Evidence export and cleanup

Download GitHub artifacts (retained 30 days) and export CloudWatch application/deployment logs before cleanup. Save CI URL, source commit, image digest, task revisions, screenshots, failure/rollback events, and measured timings. Keep local evidence out of Git. Check that logs cover the test interval, not just the latest limited API sample.

Generate a destroy plan with the same reviewed tfvars and state, review the named resources, then apply that plan after approval. ECR force_delete is disabled: export the evidence and remove only this demo repository's images before destroying it. Never delete unrelated images or a shared identity provider.

preserve_evidence_logs=true intentionally retains the two hosting log groups after Terraform destroy. They still incur storage charges. After exporting and checking the evidence, explicitly delete only /healthcare-di/dev/application and /aws/events/healthcare-di-dev. If a future project shares the GitHub OIDC provider, remove it from this project's destroy scope before cleanup. Verify no demo ALB, tasks, public IPs, ECR images, or log groups remain, and check AWS billing after usage appears.

## References

- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/alb.html
- https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_HealthCheck.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws

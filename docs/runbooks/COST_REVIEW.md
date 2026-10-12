# AWS cost and plan review â€” 2026-10-11

Account: 233781468925. Region: us-west-2 (Oregon). Environment: healthcare-di-dev.
The temporary bootstrap was created and destroyed on 2026-10-11; no ongoing hosting resources remain from that test. This document estimates costs for future hosting, not an actual invoice. Pricing was retrieved from the AWS Price List API on 2026-10-11; the response is saved in evidence/plan-review/aws-prices.json. Estimates assume 730 hours per month, Linux/x86, no free-tier credits, and one continuously running task.

| Component | Assumption | Estimated monthly USD |
|---|---|---:|
| Fargate | 0.5 vCPU at $0.040480/vCPU-hour + 1 GB at $0.004445/GB-hour | 18.02 |
| ALB | $0.0225/hour | 16.43 |
| Public IPv4 | Minimum two ALB addresses plus one task, $0.005/address-hour | 10.95 |
| Baseline subtotal | Before capacity, storage, logs, and transfer | 45.40 |
| ALB capacity example | 1 LCU continuously at $0.008/LCU-hour | 5.84 |
| Example subtotal | Baseline plus 1 LCU | 51.24 |

ECR storage/scanning, CloudWatch ingestion/storage, data transfer, DNS/certificate-related services, and usage beyond these assumptions are additional. Public IPv4 counts can grow with ALB scaling. A rollout temporarily adds a task and public IP, approximately $0.029685/hour. Optional S3/KMS resources are disabled. No NAT gateway is provisioned.

Bootstrap without a task costs approximately $0.0325/hour before ALB capacity and other usage (about $23.73/month if left running). A four-hour active demonstration with one LCU averages about $0.28 for task/ALB/three IPv4 addresses, plus temporary rollout capacity and other usage. A $5 demonstration budget provides room for these small extras; it is not an enforced spending cap. Remove resources promptly. Retained logs still incur storage charges after destroy.

## Plan boundary

The bootstrap creates the hosting foundation and GitHub OIDC roles. container_image=null defers ECS task/service creation until the publish workflow produces a validated digest. allowed_client_cidrs=[] denies client ingress. A second reviewed plan supplies the actual digest and approved access policy. Never apply a plan that contains a placeholder digest.

Review evidence/plan-review/bootstrap.txt and summary.json for the final resource count. Saved Terraform plans and state are ignored by Git. No Terraform apply runs in CI.

Pricing references: [Fargate](https://aws.amazon.com/fargate/pricing/), [ALB](https://aws.amazon.com/elasticloadbalancing/pricing/), [public IPv4](https://aws.amazon.com/vpc/pricing/).

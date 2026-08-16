# Deployment runbook

This runbook covers two independent deployment surfaces:

1. the optional AWS data and logging foundation managed by Terraform; and
2. the Streamlit dashboard, which can run directly with Python or as a container.

The current Terraform intentionally does **not** create dashboard compute. It provisions a
versioned, private, KMS-encrypted S3 bucket and an encrypted CloudWatch log group. Keeping that
boundary explicit prevents a routine portfolio demonstration from creating unreviewed cloud
compute costs.

## 1. Prerequisites

Install and verify:

- Git
- Python 3.11 or newer
- Terraform 1.6 or newer
- AWS CLI v2 for the optional AWS deployment
- Docker Desktop or another Docker Engine for the container path

Clone the repository and enter it:

```bash
git clone https://github.com/Akqadafi/healthcare-decision-intelligence-platform.git
cd healthcare-decision-intelligence-platform
```

Never commit AWS credentials, Census API keys, `.env`, Terraform state, or saved plan files.

## 2. Validate the application before deployment

Create an isolated Python environment and run the same checks used in CI:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m healthcare_di.pipeline
```

Expected results:

- lint completes without errors;
- all tests pass;
- `data/gold/mart_community_priority.csv` contains 15 Arizona counties; and
- `data/gold/data_quality_report.csv` shows every check passing.

Snapshot mode is the deployment default. It is deterministic and does not require an API key.

## 3. Deploy the Terraform foundation

### 3.1 Authenticate safely

Use an AWS profile or AWS IAM Identity Center rather than long-lived keys in the repository.

```bash
aws sso login --profile YOUR_PROFILE
aws sts get-caller-identity --profile YOUR_PROFILE
```

The returned account and ARN must match the account you intend to bill. Stop if they do not.

For the remaining commands, either add `--profile YOUR_PROFILE` to AWS CLI commands and set
`AWS_PROFILE=YOUR_PROFILE`, or use your organization's approved credential process.

### 3.2 Choose inputs

The S3 bucket name must be globally unique. A useful pattern is:

```text
community-health-intelligence-ACCOUNT_ID-REGION
```

The default region is `us-west-2` and the default environment is `portfolio`. Nothing is created
unless `deploy_cloud_resources=true` is supplied.

### 3.3 Initialize and validate

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
```

### 3.4 Create and review a saved plan

```bash
terraform -chdir=infra/terraform plan \
  -out=healthcare.tfplan \
  -var="deploy_cloud_resources=true" \
  -var="data_lake_bucket_name=YOUR-GLOBALLY-UNIQUE-NAME"

terraform -chdir=infra/terraform show healthcare.tfplan
```

The plan should contain only the expected KMS key and alias, S3 bucket controls, and CloudWatch
log group. Do not apply if the region, account, names, or resource set are unexpected.

### 3.5 Apply the reviewed plan

```bash
terraform -chdir=infra/terraform apply healthcare.tfplan
terraform -chdir=infra/terraform output
```

Record the bucket, KMS key ARN, and log-group name in your deployment evidence. Do not commit the
plan or Terraform state.

### 3.6 Verify the controls

Replace the placeholders with the Terraform outputs:

```bash
aws s3api get-public-access-block --bucket YOUR_BUCKET
aws s3api get-bucket-encryption --bucket YOUR_BUCKET
aws s3api get-bucket-versioning --bucket YOUR_BUCKET
aws logs describe-log-groups --log-group-name-prefix /community-health/portfolio/dashboard
```

Verification is successful when all four S3 public-access settings are `true`, the bucket uses
`aws:kms`, versioning is `Enabled`, and the log group reports the expected retention and KMS key.

## 4. Deploy the dashboard

### Option A: direct Python run

Use this for development, demonstrations, and data validation:

```bash
python -m healthcare_di.pipeline
streamlit run dashboard/app.py
```

Open `http://localhost:8501`. Stop the service with `Ctrl+C`.

### Option B: container run

Use this path to validate the deployable image without starting PostgreSQL:

```bash
docker build -t community-health-intelligence:local .
docker run --rm \
  --name community-health-dashboard \
  -p 8501:8501 \
  -e HDIP_LIVE_DATA=0 \
  community-health-intelligence:local
```

Open `http://localhost:8501` and verify the health endpoint:

```bash
curl --fail http://localhost:8501/_stcore/health
```

The expected response is `ok`. Stop the container with `Ctrl+C`.

### Option C: Docker Compose

The Compose profile runs the dashboard and the repository's PostgreSQL development schema:

```bash
docker compose up --build
docker compose ps
```

Open `http://localhost:8501`. When finished:

```bash
docker compose down
```

Add `--volumes` only when you intentionally want to delete the local PostgreSQL volume.

### Hosting the container

The image is portable to a managed container platform that supports:

- inbound HTTP on port `8501`;
- the health path `/_stcore/health`;
- at least 1 GB of memory for pandas, Plotly, and Streamlit; and
- `HDIP_LIVE_DATA=0` for the reproducible portfolio deployment.

Before a public healthcare deployment, add platform authentication, TLS, access logging, budget
alerts, an image registry, vulnerability scanning, and a documented rollback. The bundled public
data contains no PHI, but the current application is still a portfolio planning demonstration—not
a production clinical system.

## 5. Refreshing source data

Use the committed snapshots for normal deployment. To refresh supported public APIs:

```bash
python -m healthcare_di.pipeline --live
```

Set `CENSUS_API_KEY` only in your shell or approved secret manager when Census enrichment is
required. Review the changed snapshots, quality report, build manifest, and county rankings before
publishing a refreshed image.

## 6. Rollback

Dashboard rollback is image-based: redeploy the last known-good image tag or Git commit, then
verify `/_stcore/health` and the four dashboard tabs.

Terraform rollback should be a new reviewed plan. To remove the portfolio foundation:

```bash
terraform -chdir=infra/terraform plan -destroy \
  -out=destroy.tfplan \
  -var="deploy_cloud_resources=true" \
  -var="data_lake_bucket_name=YOUR-GLOBALLY-UNIQUE-NAME"

terraform -chdir=infra/terraform apply destroy.tfplan
```

Terraform cannot delete a non-empty S3 bucket. Export anything that must be retained, empty the
bucket deliberately, rerun the destroy plan, and verify the final resource list before applying.

## 7. Deployment checklist

- [ ] Correct AWS account and region confirmed
- [ ] Python lint, tests, and data build passed
- [ ] Terraform plan reviewed before apply
- [ ] S3 encryption, versioning, and public-access block verified
- [ ] CloudWatch retention and KMS encryption verified
- [ ] Dashboard health endpoint returned `ok`
- [ ] Executive summary, county profile, simulator, and trust center opened successfully
- [ ] Deployment evidence recorded without credentials or PHI
- [ ] Rollback target identified

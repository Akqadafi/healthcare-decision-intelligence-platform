locals {
  deploy_count = var.deploy_cloud_resources ? 1 : 0
}

resource "aws_kms_key" "data_lake" {
  count                   = local.deploy_count
  description             = "Community health public-data lake encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "data_lake" {
  count         = local.deploy_count
  name          = "alias/community-health-${var.environment}"
  target_key_id = aws_kms_key.data_lake[0].key_id
}

resource "aws_s3_bucket" "data_lake" {
  count  = local.deploy_count
  bucket = var.data_lake_bucket_name

  lifecycle {
    precondition {
      condition     = var.data_lake_bucket_name != null && length(var.data_lake_bucket_name) >= 3
      error_message = "Set data_lake_bucket_name when deploy_cloud_resources is true."
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  count                   = local.deploy_count
  bucket                  = aws_s3_bucket.data_lake[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data_lake" {
  count  = local.deploy_count
  bucket = aws_s3_bucket.data_lake[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  count  = local.deploy_count
  bucket = aws_s3_bucket.data_lake[0].id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.data_lake[0].arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  count  = local.deploy_count
  bucket = aws_s3_bucket.data_lake[0].id

  rule {
    id     = "tier-noncurrent-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

resource "aws_cloudwatch_log_group" "application" {
  count             = local.deploy_count
  name              = "/community-health/${var.environment}/dashboard"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.data_lake[0].arn
}

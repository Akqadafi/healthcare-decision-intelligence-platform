output "data_lake_bucket" {
  description = "Provisioned public aggregate data-lake bucket."
  value       = try(aws_s3_bucket.data_lake[0].id, null)
}

output "kms_key_arn" {
  description = "KMS key used by the lake and application logs."
  value       = try(aws_kms_key.data_lake[0].arn, null)
}

output "application_log_group" {
  description = "CloudWatch log group for the dashboard."
  value       = try(aws_cloudwatch_log_group.application[0].name, null)
}

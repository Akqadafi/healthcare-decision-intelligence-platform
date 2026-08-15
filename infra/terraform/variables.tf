variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "portfolio"

  validation {
    condition     = contains(["portfolio", "dev", "stage", "prod"], var.environment)
    error_message = "environment must be portfolio, dev, stage, or prod."
  }
}

variable "deploy_cloud_resources" {
  description = "Explicit cost/safety gate. Nothing is provisioned when false."
  type        = bool
  default     = false
}

variable "data_lake_bucket_name" {
  description = "Globally unique S3 bucket name; required when deployment is enabled."
  type        = string
  default     = null
  nullable    = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 30
}

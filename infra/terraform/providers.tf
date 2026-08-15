provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "community-health-intelligence"
      Environment = var.environment
      ManagedBy   = "Terraform"
      DataClass   = "PublicAggregate"
    }
  }
}

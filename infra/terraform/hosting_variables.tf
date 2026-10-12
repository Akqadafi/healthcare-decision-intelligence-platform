variable "deploy_hosting" {
  description = "Explicit hosting cost gate, independent of the optional data lake."
  type        = bool
  default     = false
}

variable "expected_account_id" {
  description = "Required account guard when hosting is enabled."
  type        = string
  default     = ""
}

variable "container_image" {
  description = "ECR image pinned by sha256 digest. Null bootstraps infrastructure without a service."
  type        = string
  default     = null
  validation {
    condition = var.container_image == null ? true : can(regex(
      "^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/[a-z0-9/_-]+@sha256:[a-f0-9]{64}$",
      var.container_image
    ))
    error_message = "Use an ECR repository@sha256:digest, never a mutable tag."
  }
}

variable "allowed_client_cidrs" {
  description = "Explicit IPv4 clients allowed to reach the ALB. Empty blocks all inbound clients."
  type        = list(string)
  default     = []
  validation {
    condition     = alltrue([for cidr in var.allowed_client_cidrs : can(cidrnetmask(cidr))])
    error_message = "Use valid IPv4 CIDRs."
  }
}

variable "certificate_arn" {
  description = "Optional ACM certificate in the same region; enables HTTPS and HTTP redirect."
  type        = string
  default     = null
}

variable "github_repository" {
  description = "Exact owner/repository authorized for OIDC, or null to omit GitHub roles."
  type        = string
  default     = null
}

variable "github_oidc_provider_arn" {
  description = "Reuse an existing GitHub provider if present; otherwise create one when GitHub is enabled."
  type        = string
  default     = null
}

variable "github_publish_environment" {
  type        = string
  default     = "dev-build"
  description = "GitHub environment trusted only to publish images."
}

variable "github_deploy_environment" {
  type        = string
  default     = "dev"
  description = "Protected GitHub environment trusted to deploy after review."
}

variable "desired_count" {
  type        = number
  default     = 1
  description = "Running tasks; demo defaults to one, with two during a rollout."
  validation {
    condition     = var.desired_count >= 1 && var.desired_count <= 4 && floor(var.desired_count) == var.desired_count
    error_message = "Choose 1–4 tasks."
  }
}

variable "preserve_evidence_logs" {
  type        = bool
  default     = true
  description = "Retain application and event log groups on destroy until evidence is exported."
}

variable "dashboard_hostname" {
  description = "DNS hostname covered by the ACM certificate; configure its CNAME to the ALB."
  type        = string
  default     = null
}

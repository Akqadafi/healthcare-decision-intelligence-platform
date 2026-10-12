output "hosting" {
  description = "Use these values for GitHub environment variables and evidence collection."
  value = var.deploy_hosting ? {
    alb_dns_name            = aws_lb.dashboard[0].dns_name
    region                  = var.aws_region
    account_id              = data.aws_caller_identity.current.account_id
    ecr_repository          = aws_ecr_repository.dashboard[0].name
    ecr_repository_url      = aws_ecr_repository.dashboard[0].repository_url
    cluster                 = aws_ecs_cluster.dashboard[0].name
    service                 = local.name
    service_created         = local.service_count == 1
    target_group_arn        = aws_lb_target_group.dashboard[0].arn
    dashboard_url           = "${var.certificate_arn == null ? "http" : "https"}://${coalesce(var.dashboard_hostname, aws_lb.dashboard[0].dns_name)}"
    application_log_group   = aws_cloudwatch_log_group.dashboard[0].name
    deployment_log_group    = aws_cloudwatch_log_group.deployments[0].name
    publish_role_arn        = try(aws_iam_role.github_publish[0].arn, null)
    deploy_role_arn         = try(aws_iam_role.github_deploy[0].arn, null)
    initial_task_definition = try(aws_ecs_task_definition.dashboard[0].arn, null)
  } : null
}

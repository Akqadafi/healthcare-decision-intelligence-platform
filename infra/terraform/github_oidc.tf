resource "aws_iam_openid_connect_provider" "github" {
  count          = local.github_count == 1 && var.github_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
locals {
  github_provider = try(coalesce(var.github_oidc_provider_arn, try(aws_iam_openid_connect_provider.github[0].arn, null)), null)
}
resource "aws_iam_role" "github_publish" {
  count = local.github_count
  name  = "${local.name}-github-publish"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Federated = local.github_provider }, Action = "sts:AssumeRoleWithWebIdentity",
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_publish_environment}"
    } }
  }] })
}
resource "aws_iam_role_policy" "github_publish" {
  count = local.github_count
  role  = aws_iam_role.github_publish[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"], Resource = aws_ecr_repository.dashboard[0].arn }
  ] })
}
resource "aws_iam_role" "github_deploy" {
  count = local.github_count
  name  = "${local.name}-github-deploy"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Federated = local.github_provider }, Action = "sts:AssumeRoleWithWebIdentity",
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_deploy_environment}"
    } }
  }] })
}
resource "aws_iam_role_policy" "github_deploy" {
  count = local.github_count
  role  = aws_iam_role.github_deploy[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecs:UpdateService"], Resource = local.service_arn },
    { Effect = "Allow", Action = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition", "ecs:DescribeServices", "ecs:ListTasks", "ecs:DescribeTasks", "ecs:ListTagsForResource", "elasticloadbalancing:DescribeTargetHealth"], Resource = "*" },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.execution[0].arn, aws_iam_role.task[0].arn], Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } } },
    { Effect = "Allow", Action = ["logs:FilterLogEvents", "logs:DescribeLogStreams", "logs:GetLogEvents"], Resource = ["${aws_cloudwatch_log_group.dashboard[0].arn}:*", "${aws_cloudwatch_log_group.deployments[0].arn}:*"] }
  ] })
}

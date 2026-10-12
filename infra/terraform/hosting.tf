data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  hosting_count = var.deploy_hosting ? 1 : 0
  service_count = var.deploy_hosting && var.container_image != null ? 1 : 0
  name          = "healthcare-di-${var.environment}"
  github_count  = var.deploy_hosting && var.github_repository != null ? 1 : 0
  service_arn   = "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${local.name}/${local.name}"
}

resource "aws_ecr_repository" "dashboard" {
  count                = local.hosting_count
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  lifecycle {
    precondition {
      condition     = var.expected_account_id == data.aws_caller_identity.current.account_id
      error_message = "Set expected_account_id to the reviewed AWS account."
    }
  }
}

resource "aws_vpc" "dashboard" {
  count                = local.hosting_count
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}
resource "aws_internet_gateway" "dashboard" {
  count  = local.hosting_count
  vpc_id = aws_vpc.dashboard[0].id
}
resource "aws_subnet" "public" {
  count             = local.hosting_count * 2
  vpc_id            = aws_vpc.dashboard[0].id
  cidr_block        = cidrsubnet("10.42.0.0/16", 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = { Name = "${local.name}-public-${count.index + 1}" }
}
resource "aws_route_table" "public" {
  count  = local.hosting_count
  vpc_id = aws_vpc.dashboard[0].id
}
resource "aws_route" "internet" {
  count                  = local.hosting_count
  route_table_id         = aws_route_table.public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.dashboard[0].id
}
resource "aws_route_table_association" "public" {
  count          = local.hosting_count * 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_security_group" "alb" {
  count       = local.hosting_count
  name        = "${local.name}-alb"
  description = "Only reviewed client CIDRs enter the dashboard."
  vpc_id      = aws_vpc.dashboard[0].id
  dynamic "ingress" {
    for_each = length(var.allowed_client_cidrs) > 0 ? [1] : []
    content {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = var.allowed_client_cidrs
    }
  }
  dynamic "ingress" {
    for_each = var.certificate_arn == null || length(var.allowed_client_cidrs) == 0 ? [] : [1]
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.allowed_client_cidrs
    }
  }
  egress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.dashboard[0].cidr_block]
  }
}
resource "aws_security_group" "task" {
  count       = local.hosting_count
  name        = "${local.name}-task"
  description = "Only the ALB can reach Streamlit; TLS egress for registry and logs."
  vpc_id      = aws_vpc.dashboard[0].id
  ingress {
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
  }
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "dashboard" {
  count                      = local.hosting_count
  name                       = local.name
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb[0].id]
  subnets                    = aws_subnet.public[*].id
  idle_timeout               = 120
  drop_invalid_header_fields = true
}
resource "aws_lb_target_group" "dashboard" {
  count                = local.hosting_count
  name                 = local.name
  port                 = 8501
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.dashboard[0].id
  deregistration_delay = 30
  health_check {
    path                = "/_stcore/health"
    port                = "traffic-port"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}
resource "aws_lb_listener" "http" {
  count             = local.hosting_count
  load_balancer_arn = aws_lb.dashboard[0].arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = var.certificate_arn == null ? "forward" : "redirect"
    target_group_arn = var.certificate_arn == null ? aws_lb_target_group.dashboard[0].arn : null
    dynamic "redirect" {
      for_each = var.certificate_arn == null ? [] : [1]
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}
resource "aws_lb_listener" "https" {
  count             = var.deploy_hosting && var.certificate_arn != null ? 1 : 0
  load_balancer_arn = aws_lb.dashboard[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  lifecycle {
    precondition {
      condition     = var.dashboard_hostname != null
      error_message = "For TLS, set dashboard_hostname to the DNS name covered by the certificate."
    }
  }
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dashboard[0].arn
  }
}

resource "aws_cloudwatch_log_group" "dashboard" {
  count             = local.hosting_count
  name              = "/healthcare-di/${var.environment}/application"
  retention_in_days = var.log_retention_days
  skip_destroy      = var.preserve_evidence_logs
}
resource "aws_cloudwatch_log_group" "deployments" {
  count             = local.hosting_count
  name              = "/aws/events/healthcare-di-${var.environment}"
  retention_in_days = var.log_retention_days
  skip_destroy      = var.preserve_evidence_logs
}
resource "aws_cloudwatch_event_rule" "deployments" {
  count = local.hosting_count
  name  = "${local.name}-deployments"
  event_pattern = jsonencode({
    source    = ["aws.ecs"], "detail-type" = ["ECS Deployment State Change"],
    resources = [local.service_arn]
  })
}
resource "aws_cloudwatch_log_resource_policy" "deployments" {
  count       = local.hosting_count
  policy_name = "${local.name}-events-to-logs"
  policy_document = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect    = "Allow", Principal = { Service = ["events.amazonaws.com", "delivery.logs.amazonaws.com"] },
      Action    = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource  = "${aws_cloudwatch_log_group.deployments[0].arn}:*",
      Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
    }]
  })
}
resource "aws_cloudwatch_event_target" "deployments" {
  count      = local.hosting_count
  rule       = aws_cloudwatch_event_rule.deployments[0].name
  target_id  = "deployment-evidence"
  arn        = aws_cloudwatch_log_group.deployments[0].arn
  depends_on = [aws_cloudwatch_log_resource_policy.deployments]
}

resource "aws_iam_role" "execution" {
  count = local.hosting_count
  name  = "${local.name}-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}
resource "aws_iam_role_policy" "execution" {
  count = local.hosting_count
  role  = aws_iam_role.execution[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = aws_ecr_repository.dashboard[0].arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.dashboard[0].arn}:*" }
  ] })
}
resource "aws_iam_role" "task" {
  count              = local.hosting_count
  name               = "${local.name}-task"
  assume_role_policy = aws_iam_role.execution[0].assume_role_policy
  # Bundled snapshots require no AWS application permissions.
}
resource "aws_ecs_cluster" "dashboard" {
  count = local.hosting_count
  name  = local.name
}
resource "aws_ecs_task_definition" "dashboard" {
  count                    = local.service_count
  family                   = local.name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution[0].arn
  task_role_arn            = aws_iam_role.task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name         = "dashboard", image = var.container_image, essential = true,
    portMappings = [{ containerPort = 8501, hostPort = 8501, protocol = "tcp" }],
    environment  = [{ name = "HDIP_LIVE_DATA", value = "0" }],
    healthCheck = {
      command  = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"],
      interval = 30, timeout = 5, retries = 3, startPeriod = 60
    },
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group  = aws_cloudwatch_log_group.dashboard[0].name,
      awslogs-region = var.aws_region, awslogs-stream-prefix = "dashboard"
    } }
  }])
  lifecycle {
    precondition {
      condition     = startswith(var.container_image, "${aws_ecr_repository.dashboard[0].repository_url}@sha256:")
      error_message = "The initial image must come from this deployment's ECR repository."
    }
  }
}
resource "aws_ecs_service" "dashboard" {
  count                              = local.service_count
  name                               = local.name
  cluster                            = aws_ecs_cluster.dashboard[0].id
  task_definition                    = aws_ecs_task_definition.dashboard[0].arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  health_check_grace_period_seconds  = 120
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  deployment_controller { type = "ECS" }
  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.task[0].id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.dashboard[0].arn
    container_name   = "dashboard"
    container_port   = 8501
  }
  depends_on = [aws_lb_listener.http, aws_lb_listener.https, aws_iam_role_policy.execution,
  aws_route.internet, aws_route_table_association.public, aws_cloudwatch_event_target.deployments]
  lifecycle {
    # Release workflows own this pointer; Terraform must not silently undo a rollout/rollback.
    ignore_changes = [task_definition]
  }
}

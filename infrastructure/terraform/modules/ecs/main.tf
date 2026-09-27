locals {
  name = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Module = "ecs"
  })

  env_vars = [
    for k, v in var.environment_variables : {
      name  = k
      value = v
    }
  ]

  secret_refs = [
    for k, arn in var.secrets_arns : {
      name      = k
      valueFrom = arn
    }
  ]
}

# ── ECS cluster ─────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

# ── Security group rules for ECS tasks (SG created in environment config) ──
resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = var.task_security_group_id
  referenced_security_group_id = var.alb_security_group_id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  security_group_id = var.task_security_group_id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ── IAM: task execution role (pull images, push logs, read secrets)
resource "aws_iam_role" "execution" {
  name = "${local.name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_base" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_policy" "execution_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0

  name = "${local.name}-ecs-execution-secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = values(var.secrets_arns)
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0

  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution_secrets[0].arn
}

# ── IAM: task role (app-level permissions: S3, etc.) ────────────
resource "aws_iam_role" "task" {
  name = "${local.name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

# ── API task definition ─────────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = local.env_vars
    secrets     = local.secret_refs

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "api"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
  }])

  tags = local.common_tags
}

# ── Worker task definition ──────────────────────────────────────
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true
    command   = ["python", "-m", "researchforge.workers.run"]

    environment = local.env_vars
    secrets     = local.secret_refs

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])

  tags = local.common_tags
}

# ── API service ─────────────────────────────────────────────────
resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.task_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}

# ── Worker service ──────────────────────────────────────────────
resource "aws_ecs_service" "worker" {
  name            = "${local.name}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.task_security_group_id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}

# ── Data source ─────────────────────────────────────────────────
data "aws_region" "current" {}

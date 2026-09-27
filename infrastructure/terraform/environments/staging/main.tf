terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "researchforge-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "researchforge-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = "staging"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  environment    = "staging"
  name           = "${var.project}-${local.environment}"
  log_group_name = "/ecs/${local.name}"
}

# ── Networking ──────────────────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  project     = var.project
  environment = local.environment
  az_count    = 2
}

# ── ECS task security group (created here to break circular deps)
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${local.name}-ecs-"
  description = "ECS task network access"
  vpc_id      = module.vpc.vpc_id

  tags = {
    Name = "${local.name}-ecs-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ── Container registry ──────────────────────────────────────────
module "ecr" {
  source = "../../modules/ecr"

  project     = var.project
  environment = local.environment
}

# ── Data stores ─────────────────────────────────────────────────
module "rds" {
  source = "../../modules/rds"

  project     = var.project
  environment = local.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  allowed_security_group_ids = [aws_security_group.ecs_tasks.id]

  instance_class      = "db.t3.micro"
  multi_az            = false
  deletion_protection = false
}

module "elasticache" {
  source = "../../modules/elasticache"

  project     = var.project
  environment = local.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  allowed_security_group_ids = [aws_security_group.ecs_tasks.id]

  node_type = "cache.t3.micro"
}

module "s3" {
  source = "../../modules/s3"

  project       = var.project
  environment   = local.environment
  force_destroy = true
}

# ── Secrets ─────────────────────────────────────────────────────
module "secrets" {
  source = "../../modules/secrets"

  project     = var.project
  environment = local.environment
}

# ── Monitoring ──────────────────────────────────────────────────
module "monitoring" {
  source = "../../modules/monitoring"

  project     = var.project
  environment = local.environment

  log_group_name      = local.log_group_name
  ecs_cluster_name    = module.ecs.cluster_name
  api_service_name    = module.ecs.api_service_name
  worker_service_name = module.ecs.worker_service_name
  log_retention_days  = 14
}

# ── Load balancer ───────────────────────────────────────────────
module "alb" {
  source = "../../modules/alb"

  project     = var.project
  environment = local.environment

  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
}

# ── Compute ─────────────────────────────────────────────────────
module "ecs" {
  source = "../../modules/ecs"

  project     = var.project
  environment = local.environment

  private_subnet_ids    = module.vpc.private_subnet_ids
  task_security_group_id = aws_security_group.ecs_tasks.id
  alb_security_group_id = module.alb.security_group_id
  target_group_arn      = module.alb.target_group_arn
  ecr_repository_url    = module.ecr.repository_url
  log_group_name        = local.log_group_name

  api_cpu           = 256
  api_memory        = 512
  api_desired_count = 1

  worker_cpu           = 256
  worker_memory        = 512
  worker_desired_count = 1

  environment_variables = {
    APP_ENV   = "staging"
    APP_NAME  = "researchforge-ai"
    REDIS_URL = module.elasticache.redis_url
  }

  secrets_arns = module.secrets.secret_arns
}

# ── S3 access for ECS tasks ────────────────────────────────────
resource "aws_iam_role_policy" "ecs_s3_access" {
  name = "${var.project}-staging-ecs-s3"
  role = module.ecs.task_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
      ]
      Resource = [
        module.s3.bucket_arn,
        "${module.s3.bucket_arn}/*",
      ]
    }]
  })
}

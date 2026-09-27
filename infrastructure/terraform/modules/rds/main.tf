locals {
  name = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Module = "rds"
  })
}

# ── Subnet group ────────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = var.subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.name}-db-subnet-group"
  })
}

# ── Security group ──────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name_prefix = "${local.name}-rds-"
  description = "Allow PostgreSQL access from ECS tasks"
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, {
    Name = "${local.name}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds" {
  count = length(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = var.allowed_security_group_ids[count.index]
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# ── RDS instance ────────────────────────────────────────────────
resource "aws_db_instance" "main" {
  identifier = "${local.name}-postgres"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.allocated_storage * 2
  storage_encrypted     = true

  db_name  = var.db_name
  username = "researchforge"

  manage_master_user_password = true

  multi_az            = var.multi_az
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = var.backup_retention_period
  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name}-final-snapshot" : null

  performance_insights_enabled = true

  tags = merge(local.common_tags, {
    Name = "${local.name}-postgres"
  })
}

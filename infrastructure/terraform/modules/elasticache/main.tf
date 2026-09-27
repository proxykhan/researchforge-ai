locals {
  name = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Module = "elasticache"
  })
}

# ── Subnet group ────────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-redis"
  subnet_ids = var.subnet_ids

  tags = local.common_tags
}

# ── Security group ──────────────────────────────────────────────
resource "aws_security_group" "redis" {
  name_prefix = "${local.name}-redis-"
  description = "Allow Redis access from ECS tasks"
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, {
    Name = "${local.name}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "redis" {
  count = length(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.redis.id
  referenced_security_group_id = var.allowed_security_group_ids[count.index]
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

# ── ElastiCache cluster ─────────────────────────────────────────
resource "aws_elasticache_cluster" "main" {
  cluster_id = "${local.name}-redis"

  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  transit_encryption_enabled = true

  tags = merge(local.common_tags, {
    Name = "${local.name}-redis"
  })
}

locals {
  name = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Module = "secrets"
  })
}

resource "aws_secretsmanager_secret" "app" {
  for_each = var.secrets

  name        = "${local.name}/${each.key}"
  description = each.value

  tags = merge(local.common_tags, {
    Name = "${local.name}-${each.key}"
  })
}

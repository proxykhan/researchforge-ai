locals {
  common_tags = merge(var.tags, {
    Module = "github-oidc"
  })
}

# ── OIDC identity provider ─────────────────────────────────────
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# ── IAM role for GitHub Actions ─────────────────────────────────
resource "aws_iam_role" "github_actions" {
  name = "${var.project}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
        }
      }
    }]
  })

  tags = local.common_tags
}

# ── ECR push permissions ───────────────────────────────────────
resource "aws_iam_policy" "ecr_push" {
  count = length(var.ecr_repository_arns) > 0 ? 1 : 0

  name = "${var.project}-github-ecr-push"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = var.ecr_repository_arns
      },
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecr_push" {
  count = length(var.ecr_repository_arns) > 0 ? 1 : 0

  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecr_push[0].arn
}

# ── ECS deploy permissions ─────────────────────────────────────
resource "aws_iam_policy" "ecs_deploy" {
  count = length(var.ecs_cluster_arns) > 0 ? 1 : 0

  name = "${var.project}-github-ecs-deploy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:ListTasks",
          "ecs:DescribeTasks",
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "ecs:cluster" = var.ecs_cluster_arns
          }
        }
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "ecs-tasks.amazonaws.com"
          }
        }
      },
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_deploy" {
  count = length(var.ecs_cluster_arns) > 0 ? 1 : 0

  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecs_deploy[0].arn
}

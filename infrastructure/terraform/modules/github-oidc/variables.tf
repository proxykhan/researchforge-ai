variable "project" {
  type = string
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs that CI/CD can push to"
  type        = list(string)
  default     = []
}

variable "ecs_cluster_arns" {
  description = "ECS cluster ARNs that CI/CD can deploy to"
  type        = list(string)
  default     = []
}

variable "ecs_service_arns" {
  description = "ECS service ARNs that CI/CD can update"
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

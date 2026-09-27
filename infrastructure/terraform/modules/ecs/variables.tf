variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "task_security_group_id" {
  description = "Security group ID for ECS tasks (created externally to avoid circular deps)"
  type        = string
}

variable "alb_security_group_id" {
  description = "ALB security group ID (allowed to reach ECS tasks)"
  type        = string
}

variable "target_group_arn" {
  description = "ALB target group ARN for the API service"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for the application image"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "api_cpu" {
  description = "API task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "API task memory in MB"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Number of API tasks"
  type        = number
  default     = 1
}

variable "worker_cpu" {
  description = "Worker task CPU units"
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Worker task memory in MB"
  type        = number
  default     = 512
}

variable "worker_desired_count" {
  description = "Number of worker tasks"
  type        = number
  default     = 1
}

variable "secrets_arns" {
  description = "Map of secret name to Secrets Manager ARN for ECS task environment"
  type        = map(string)
  default     = {}
}

variable "environment_variables" {
  description = "Map of environment variable name to value for ECS tasks"
  type        = map(string)
  default     = {}
}

variable "log_group_name" {
  description = "CloudWatch log group name"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

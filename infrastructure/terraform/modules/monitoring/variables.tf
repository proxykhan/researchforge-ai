variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name for dashboard metrics"
  type        = string
}

variable "api_service_name" {
  description = "API ECS service name"
  type        = string
}

variable "worker_service_name" {
  description = "Worker ECS service name"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for CloudWatch metrics"
  type        = string
  default     = ""
}

variable "rds_instance_id" {
  description = "RDS instance identifier for alarms"
  type        = string
  default     = ""
}

variable "log_group_name" {
  description = "CloudWatch log group name (passed in to avoid circular dependency with ECS)"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications (empty = no alarms)"
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

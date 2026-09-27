variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB"
  type        = list(string)
}

variable "health_check_path" {
  description = "Health check path for the target group"
  type        = string
  default     = "/api/v1/health"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (empty = HTTP only)"
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

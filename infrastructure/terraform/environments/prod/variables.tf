variable "project" {
  type    = string
  default = "researchforge"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS on the ALB"
  type        = string
  default     = ""
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

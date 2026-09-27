variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "force_destroy" {
  description = "Allow bucket destruction even with objects (non-prod only)"
  type        = bool
  default     = false
}

variable "tags" {
  type    = map(string)
  default = {}
}

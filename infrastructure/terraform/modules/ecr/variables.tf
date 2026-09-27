variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "image_retention_count" {
  description = "Number of images to retain per repository"
  type        = number
  default     = 10
}

variable "tags" {
  type    = map(string)
  default = {}
}

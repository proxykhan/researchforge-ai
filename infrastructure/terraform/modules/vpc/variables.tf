variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "cidr_block" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
}

variable "tags" {
  type    = map(string)
  default = {}
}

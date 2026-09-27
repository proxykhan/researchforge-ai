variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "secrets" {
  description = "Map of secret name to description (values are set manually in AWS console)"
  type        = map(string)
  default = {
    "anthropic-api-key"        = "Anthropic API key for LLM calls"
    "semantic-scholar-api-key" = "Semantic Scholar API key"
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}

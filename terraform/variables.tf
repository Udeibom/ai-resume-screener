variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}
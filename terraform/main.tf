terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Secure Elastic Container Registry (ECR) to hold our API Docker images
resource "aws_ecr_repository" "api_repo" {
  name                 = "ai-resume-screener-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true # Automatically audit code dependencies for vulnerability leaks
  }

  tags = {
    Environment = var.environment
    Project     = "AI-Resume-Screener"
  }
}
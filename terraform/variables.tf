variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "production"
}

output "ecr_repository_url" {
  description = "The target cloud URI to point your Docker image push commands towards."
  value       = aws_ecr_repository.api_repo.repository_url
}

output "s3_bucket_name" {
  description = "The unique cloud reference name generated for storage integrations."
  value       = aws_s3_bucket.resume_storage.id
}
# 2. Dedicated secure AWS S3 Bucket for raw resume PDF file storage
resource "aws_s3_bucket" "resume_storage" {
  bucket        = "ai-resume-screener-storage-${var.environment}"
  force_destroy = true # Allows easy cleanup during portfolio demonstrations

  tags = {
    Environment = var.environment
    Project     = "AI-Resume-Screener"
  }
}

# Enforce strict private isolation on the storage layer
resource "aws_s3_bucket_public_access_block" "private_block" {
  bucket = aws_s3_bucket.resume_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
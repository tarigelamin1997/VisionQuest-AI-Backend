provider "aws" {
  region = "us-east-1"
}

# 1. The Container Registry (Where the Docker Image lives)
resource "aws_ecr_repository" "etl_repo" {
  name                 = "visionquest-etl"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# 2. Output the URL (We need this to push the image)
output "repository_url" {
  value       = aws_ecr_repository.etl_repo.repository_url
  description = "The URL of the ECR repository"
}
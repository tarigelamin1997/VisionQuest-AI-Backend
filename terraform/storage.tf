# 1. MAIN DATA LAKE BUCKET
resource "aws_s3_bucket" "data_lake" {
  bucket_prefix = "visionquest-data-"
  force_destroy = true # Allows deleting bucket even if it has files (for dev)
}

# 2. PUBLIC ACCESS BLOCK (Security Best Practice)
resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# OUTPUT (Backend needs this to know where to upload)
output "s3_bucket_name" {
  value = aws_s3_bucket.data_lake.id
}
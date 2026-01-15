# 1. JOBS TABLE (Tracks async processing status)
resource "aws_dynamodb_table" "jobs_table" {
  name           = "VisionQuest_Jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"

  # Primary Key
  attribute {
    name = "job_id"
    type = "S"
  }

  # --- NEW: Attributes for the Chat History Index ---
  attribute {
    name = "chat_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }
  # --------------------------------------------------

  # Automatically delete old job records after 24 hours (Cost savings)
  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  # --- NEW: The Index (Lookup by Chat ID) ---
  global_secondary_index {
    name               = "ChatIndex"
    hash_key           = "chat_id"
    range_key          = "created_at" # Sort messages chronologically
    projection_type    = "ALL"
  }
  # ------------------------------------------

  tags = {
    Name = "VisionQuest Job Tracker"
  }
}

# 2. CHATS TABLE (Tracks User History Metadata)
resource "aws_dynamodb_table" "chats_table" {
  name           = "VisionQuest_Chats"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "chat_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "chat_id"
    type = "S"
  }

  tags = {
    Name = "VisionQuest Chat History"
  }
}

# OUTPUTS (Required for Lambda Environment Variables)
output "jobs_table_name" {
  value = aws_dynamodb_table.jobs_table.name
}

output "chats_table_name" {
  value = aws_dynamodb_table.chats_table.name
}
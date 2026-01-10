# --- CONFIGURATION ---
variable "bucket_name" {
  default = "visionquest-kb-tarig-001" # <--- VERIFY THIS NAME
}

variable "app_name" {
  default = "VisionQuest"
}

# 1. DATA SOURCES
data "aws_s3_bucket" "kb_bucket" {
  bucket = var.bucket_name
}

data "aws_dynamodb_table" "logs" {
  name = "VisionQuest_Ingestion_Logs"
}

# 2. THE QUEUES (Decoupling Layer)

# A. Dead Letter Queue (The "Safety Net" for failed jobs)
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.app_name}-DLQ"
  message_retention_seconds = 1209600 # 14 days to debug failures
}

# B. Main Job Queue (The "Buffer")
resource "aws_sqs_queue" "job_queue" {
  name                       = "${var.app_name}-JobQueue"
  visibility_timeout_seconds = 70 # Must be > Lambda timeout (60s)
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3 # Try 3 times, then send to DLQ
  })
}

# 3. PERMISSIONS (IAM)

resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.app_name}_Policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Logging
      {
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      # S3 Access
      {
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = "${data.aws_s3_bucket.kb_bucket.arn}/*"
      },
      # SQS Access (Worker needs to pull jobs)
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = aws_sqs_queue.job_queue.arn
      },
      # Translate & DynamoDB
      {
        Action   = ["translate:TranslateText", "dynamodb:PutItem"]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# 4. S3 NOTIFICATION (The Trigger)
# Instead of triggering Lambda directly, S3 triggers the Queue.

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = data.aws_s3_bucket.kb_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.job_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "raw/"
  }
}

# Allow S3 to write to the Queue
resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.job_queue.id
  policy    = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.job_queue.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = data.aws_s3_bucket.kb_bucket.arn }
      }
    }]
  })
}

# 5. THE LAMBDA WORKER (The "Heavy Lifter")

resource "aws_lambda_function" "etl_processor" {
  function_name = "${var.app_name}_Worker"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.etl_repo.repository_url}:latest"
  
  # --- RELIABILITY UPGRADES ---
  timeout       = 60   # Increased from 3s to 60s (User Request)
  memory_size   = 1024 # Increased RAM for faster processing
  
  environment {
    variables = {
      DYNAMO_TABLE  = data.aws_dynamodb_table.logs.name
      TARGET_BUCKET = var.bucket_name
    }
  }
}

# 6. CONNECT SQS -> LAMBDA
# This automatically wakes up Lambda when items land in the Queue
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.job_queue.arn
  function_name    = aws_lambda_function.etl_processor.arn
  batch_size       = 1  # Process 1 file at a time (Safer for heavy AI tasks)
}
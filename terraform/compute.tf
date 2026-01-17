# --- 1. ARCHIVE THE CODE ---
data "archive_file" "ingest_zip" {
  type        = "zip"
  source_dir  = "../backend/ingest"
  output_path = "ingest.zip"
}

data "archive_file" "processor_zip" {
  type        = "zip"
  source_dir  = "../backend/processor"
  output_path = "processor.zip"
}

data "archive_file" "status_zip" {
  type        = "zip"
  source_dir  = "../backend/status"
  output_path = "status.zip"
}

# --- 2. INGEST LAMBDA (The Receptionist) ---
# --- 2. INGEST LAMBDA (The Receptionist) ---
resource "aws_lambda_function" "ingest_lambda" {
  filename      = "ingest.zip"
  function_name = "VisionQuest_Ingest"
  role          = aws_iam_role.backend_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.9"
  source_code_hash = data.archive_file.ingest_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME  = aws_dynamodb_table.jobs_table.name
      CHATS_TABLE_NAME = aws_dynamodb_table.chats_table.name  # <--- NEW LINE
      BUCKET_NAME      = aws_s3_bucket.data_lake.id
    }
  }
}

# --- 3. PROCESSOR LAMBDA (The Worker) ---
resource "aws_lambda_function" "processor_lambda" {
  filename      = "processor.zip"
  function_name = "VisionQuest_Processor"
  role          = aws_iam_role.backend_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300 
  memory_size   = 1024 
  source_code_hash = data.archive_file.processor_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.jobs_table.name
      KB_ID           = aws_bedrockagent_knowledge_base.main_kb.id
      MODEL_ARN       = "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
    }
  }
}

# --- 4. STATUS LAMBDA (The Check-In) ---
resource "aws_lambda_function" "status_lambda" {
  filename      = "status.zip"
  function_name = "VisionQuest_Status"
  role          = aws_iam_role.backend_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.9"
  source_code_hash = data.archive_file.status_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.jobs_table.name
    }
  }
}

# --- 5. S3 TRIGGER (The Handshake) ---
resource "aws_s3_bucket_notification" "trigger_processor" {
  bucket = aws_s3_bucket.data_lake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor_lambda.arn
    events              = ["s3:ObjectCreated:*"] # Captures Put, Post, and Multi-part
  }
  
  # CRITICAL: Ensures S3 is allowed to talk to Lambda BEFORE creating trigger
  depends_on = [aws_lambda_permission.allow_s3_processor] 
}

resource "aws_lambda_permission" "allow_s3_processor" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_lake.arn # Restricts access to ONLY your bucket
}

# --- 6. HISTORY LAMBDA (The Memory) ---
data "archive_file" "history_zip" {
  type        = "zip"
  source_dir  = "../backend/history"
  output_path = "history.zip"
}

resource "aws_lambda_function" "history_lambda" {
  filename      = "history.zip"
  function_name = "VisionQuest_History"
  role          = aws_iam_role.backend_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.9"
  source_code_hash = data.archive_file.history_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME  = aws_dynamodb_table.jobs_table.name
      CHATS_TABLE_NAME = aws_dynamodb_table.chats_table.name
    }
  }
}


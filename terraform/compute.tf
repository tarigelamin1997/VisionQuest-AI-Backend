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

data "archive_file" "history_zip" {
  type        = "zip"
  source_dir  = "../backend/history"
  output_path = "history.zip"
}

# --- NEW: KICKOFF LAMBDA ARCHIVE ---
data "archive_file" "kickoff_zip" {
  type        = "zip"
  source_dir  = "../backend/kickoff"
  output_path = "kickoff.zip"
}

# --- 2. INGEST LAMBDA (The Receptionist) ---
resource "aws_lambda_function" "ingest_lambda" {
  filename         = "ingest.zip"
  function_name    = "VisionQuest_Ingest"
  role             = aws_iam_role.backend_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.ingest_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME  = aws_dynamodb_table.jobs_table.name
      CHATS_TABLE_NAME = aws_dynamodb_table.chats_table.name
      s3_bucket_name   = aws_s3_bucket.data_lake.id
    }
  }
}

# --- 3. PROCESSOR LAMBDA (The Brain) ---
# Note: No longer triggered by S3. Triggered by Step Functions.
resource "aws_lambda_function" "processor_lambda" {
  filename         = "processor.zip"
  function_name    = "VisionQuest_Processor"
  role             = aws_iam_role.backend_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300 # 5 Minutes for deep thinking
  source_code_hash = data.archive_file.processor_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.jobs_table.name
      # Using the specific Inference Profile ARN provided
      MODEL_ARN       = "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
    }
  }
}

# --- 4. STATUS LAMBDA (The Tracker) ---
resource "aws_lambda_function" "status_lambda" {
  filename         = "status.zip"
  function_name    = "VisionQuest_Status"
  role             = aws_iam_role.backend_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.status_zip.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.jobs_table.name
    }
  }
}

# --- 5. HISTORY LAMBDA (The Memory) ---
resource "aws_lambda_function" "history_lambda" {
  filename         = "history.zip"
  function_name    = "VisionQuest_History"
  role             = aws_iam_role.backend_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.history_zip.output_base64sha256

  environment {
    variables = {
      CHATS_TABLE_NAME = aws_dynamodb_table.chats_table.name
      JOBS_TABLE_NAME  = aws_dynamodb_table.jobs_table.name
    }
  }
}

# --- 6. KICKOFF LAMBDA (The Trigger) ---
resource "aws_lambda_function" "kickoff_lambda" {
  filename         = "kickoff.zip"
  function_name    = "VisionQuest_Kickoff"
  role             = aws_iam_role.backend_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.kickoff_zip.output_base64sha256

  environment {
    variables = {
      # Links to the State Machine defined in step_functions.tf
      STATE_MACHINE_ARN = aws_sfn_state_machine.visionquest_pipeline.arn
    }
  }
}

# --- 7. S3 TRIGGER (S3 -> Kickoff Only) ---
resource "aws_s3_bucket_notification" "trigger_kickoff" {
  bucket = aws_s3_bucket.data_lake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.kickoff_lambda.arn
    events              = ["s3:ObjectCreated:*"] 
  }
  
  depends_on = [aws_lambda_permission.allow_s3_kickoff] 
}

resource "aws_lambda_permission" "allow_s3_kickoff" {
  statement_id  = "AllowS3InvokeKickoff"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kickoff_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_lake.arn 
}

# --- 8. IAM PERMISSIONS (Backend Role -> Step Function) ---
resource "aws_iam_role_policy" "allow_start_execution" {
  name = "AllowStartSFN"
  role = aws_iam_role.backend_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "states:StartExecution"
      Effect = "Allow"
      Resource = aws_sfn_state_machine.visionquest_pipeline.arn
    }]
  })
}

# --- DATA HELPERS ---
data "aws_caller_identity" "current" {}
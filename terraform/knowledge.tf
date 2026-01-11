# -----------------------------------------------------------------------------
# 1. The Buckets (Inbox & Outbox)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "raw_knowledge" {
  bucket = "visionquest-kb-raw-${var.project_id}" # Ensure project_id var is defined
}

resource "aws_s3_bucket" "clean_knowledge" {
  bucket = "visionquest-kb-clean-${var.project_id}"
}

# -----------------------------------------------------------------------------
# 2. The IAM Role (The Badge)
# Grants the Lambda permission to use Textract, S3, and Logging.
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ocr_role" {
  name = "VisionQuest_OCR_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ocr_policy" {
  name = "VisionQuest_OCR_Permissions"
  role = aws_iam_role.ocr_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["textract:DetectDocumentText", "textract:AnalyzeDocument"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject"]
        Resource = [
          "${aws_s3_bucket.raw_knowledge.arn}/*",
          "${aws_s3_bucket.clean_knowledge.arn}/*"
        ]
      },
      {
        # Network Interface Permissions (Required for VPC)
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 3. The Cleaner Agent (Lambda) - DEPLOYED INSIDE VPC
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "ocr_cleaner" {
  filename      = "ocr_worker.zip"
  function_name = "VisionQuest_OCR_Agent"
  role          = aws_iam_role.ocr_role.arn
  handler       = "ocr_worker.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300
  memory_size   = 512

  # !!! CRITICAL: Lock this Lambda in the Vault !!!
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      CLEAN_BUCKET = aws_s3_bucket.clean_knowledge.bucket
    }
  }
}

# -----------------------------------------------------------------------------
# 4. The Trigger (Automation)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket_notification" "trigger_ocr" {
  bucket = aws_s3_bucket.raw_knowledge.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ocr_cleaner.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".pdf"
  }
}

# Allow S3 to call the Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ocr_cleaner.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_knowledge.arn
}
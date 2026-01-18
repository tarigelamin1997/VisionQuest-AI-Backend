# -----------------------------------------------------------------------------
# 1. The Buckets (Inbox & Outbox)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "raw_knowledge" {
  bucket = "visionquest-kb-raw-${var.project_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "clean_knowledge" {
  bucket = "visionquest-kb-clean-${var.project_id}"
  force_destroy = true
}

# -----------------------------------------------------------------------------
# 2. The IAM Role (The Badge)
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
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject"]
        Resource = [
          "${aws_s3_bucket.raw_knowledge.arn}/*",
          "${aws_s3_bucket.clean_knowledge.arn}/*",
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
            "textract:DetectDocumentText",
            "textract:AnalyzeDocument",
            "textract:StartDocumentTextDetection", 
            "textract:GetDocumentTextDetection"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 3. The Lambda Agent (The Accountant)
# -----------------------------------------------------------------------------
# Re-using the ingest folder source, assuming ocr_worker.py is located there
data "archive_file" "ocr_zip" {
  type        = "zip"
  source_dir  = "../backend/ingest" 
  output_path = "ocr_worker.zip"
}

resource "aws_lambda_function" "ocr_cleaner" {
  filename         = "ocr_worker.zip"
  function_name    = "VisionQuest_OCR_Agent"
  role             = aws_iam_role.ocr_role.arn
  handler          = "ocr_worker.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  memory_size      = 512
  source_code_hash = data.archive_file.ocr_zip.output_base64sha256

  # REMOVED: vpc_config block (Public Access enabled for reliability)

  environment {
    variables = {
      CLEAN_BUCKET = aws_s3_bucket.clean_knowledge.bucket
    }
  }
}
# -----------------------------------------------------------------------------
# IAM Role for General Backend Lambdas (Ingest, Status, History, etc.)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "backend_role" {
  name = "VisionQuest_Backend_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# -----------------------------------------------------------------------------
# Permissions Policy (The Badge Access)
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy" "backend_policy" {
  name = "VisionQuest_Backend_Permissions"
  role = aws_iam_role.backend_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # 1. Logging (Basic Requirement)
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # 2. Database Access (Read/Write Jobs & Chats)
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "*"
      },
      # 3. Storage Access (Save PDFs)
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      # 4. Orchestration (Trigger Step Functions)
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = "*"
      },
      # 5. AI Access (Talk to Bedrock)
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      }
    ]
  })
}
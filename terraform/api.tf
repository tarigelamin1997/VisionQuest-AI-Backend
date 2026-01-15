# -----------------------------------------------------------------------------
# 1. The Brain Role (IAM)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "backend_role" {
  name = "VisionQuest_Backend_Role"

  # Trust Policy: Who can assume this role? (Lambdas)
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Permissions Policy: What can the role DO?
resource "aws_iam_role_policy" "backend_permissions" {
  name = "VisionQuest_Backend_Permissions"
  role = aws_iam_role.backend_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # 1. Logging
      {
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      # 2. Bedrock & Marketplace
      {
        Action   = [
          "bedrock:RetrieveAndGenerate",
          "bedrock:Retrieve",
          "bedrock:InvokeModel",
          "bedrock:GetInferenceProfile",
          "aws-marketplace:ViewSubscriptions",
          "aws-marketplace:Subscribe",
          "aws-marketplace:Unsubscribe"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      # 3. S3 Access
      {
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Effect   = "Allow"
        Resource = "*" 
      },
      # 4. Transcribe Access
      {
        Action   = ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"]
        Effect   = "Allow"
        Resource = "*"
      },
      # 5. DynamoDB Access (Moved here correctly)
      {
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"]
        Effect   = "Allow"
        Resource = "*" 
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 2. The Public Gate (API Gateway V2)
# -----------------------------------------------------------------------------

# DEFINITION (Restored!)
resource "aws_apigatewayv2_api" "visionquest_api" {
  name          = "VisionQuest-Public-API"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"] # Added GET for Status checks
    allow_headers = ["content-type"]
  }
}

# STAGE (Restored!)
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.visionquest_api.id
  name        = "$default"
  auto_deploy = true
}

# --- ROUTE 1: INGEST (POST /chat/submit) ---
resource "aws_apigatewayv2_integration" "ingest_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.ingest_lambda.invoke_arn
}

resource "aws_apigatewayv2_route" "submit_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /submit"
  target    = "integrations/${aws_apigatewayv2_integration.ingest_integration.id}"
}

# --- ROUTE 2: STATUS (POST /chat/status) ---
resource "aws_apigatewayv2_integration" "status_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.status_lambda.invoke_arn
}

resource "aws_apigatewayv2_route" "status_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /status" 
  target    = "integrations/${aws_apigatewayv2_integration.status_integration.id}"
}

# --- PERMISSIONS (Allow API Gateway to call Lambdas) ---
resource "aws_lambda_permission" "api_gw_ingest" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_status" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

# --- ROUTE 3: HISTORY (GET /history) ---
resource "aws_apigatewayv2_integration" "history_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.history_lambda.invoke_arn
}

resource "aws_apigatewayv2_route" "history_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "GET /history"
  target    = "integrations/${aws_apigatewayv2_integration.history_integration.id}"
}
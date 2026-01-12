# -----------------------------------------------------------------------------
# 1. The Brain Role (IAM)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "backend_role" {
  name = "VisionQuest_Backend_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

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
      # 3. S3 Access (For saving audio files)
      {
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Effect   = "Allow"
        Resource = "*" 
      },
      # 4. Transcribe Access (The New Power)
      {
        Action   = ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 2. The Brain Function (Lambda)
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "backend_api" {
  filename      = "backend.zip"
  function_name = "VisionQuest_API_Handler"
  role          = aws_iam_role.backend_role.arn
  handler       = "app.lambda_handler"
  runtime       = "python3.9"
  timeout       = 60
  memory_size   = 512
  
  source_code_hash = filebase64sha256("backend.zip")

  environment {
    variables = {
      KB_ID      = aws_bedrockagent_knowledge_base.main_kb.id
      MODEL_ARN  = "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
      # NEW VARIABLE: Reuse your raw bucket for audio
      BUCKET_NAME = "visionquest-kb-raw-visionquest-dev-tarig-001" 
    }
  }
}

# -----------------------------------------------------------------------------
# 3. The Public Gate (API Gateway V2)
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "visionquest_api" {
  name          = "VisionQuest-Public-API"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.visionquest_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.backend_api.invoke_arn
}

resource "aws_apigatewayv2_route" "chat_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

output "api_url" {
  value = "${aws_apigatewayv2_api.visionquest_api.api_endpoint}/chat"
}
# -----------------------------------------------------------------------------
# 1. The API Gateway (The Front Door)
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "visionquest_api" {
  name          = "VisionQuest-API-${var.project_id}"
  protocol_type = "HTTP"

  # CORS Configuration (Critical for Streamlit/Browser access)
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }
}

# -----------------------------------------------------------------------------
# 2. The Stage (Production Environment)
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_stage" "prod_stage" {
  api_id      = aws_apigatewayv2_api.visionquest_api.id
  name        = "$default" # Makes the URL shorter (no /prod needed)
  auto_deploy = true       # CRITICAL: Automatically updates when you change Terraform
}

# -----------------------------------------------------------------------------
# 3. Integrations (Connecting API -> Lambda)
# -----------------------------------------------------------------------------

# --- INGEST INTEGRATION ---
resource "aws_apigatewayv2_integration" "ingest_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.ingest_lambda.invoke_arn
  payload_format_version = "2.0"
}

# --- STATUS INTEGRATION ---
resource "aws_apigatewayv2_integration" "status_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.status_lambda.invoke_arn
  payload_format_version = "2.0"
}

# --- HISTORY INTEGRATION ---
resource "aws_apigatewayv2_integration" "history_integration" {
  api_id           = aws_apigatewayv2_api.visionquest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.history_lambda.invoke_arn
  payload_format_version = "2.0"
}

# -----------------------------------------------------------------------------
# 4. Routes (The Map: /path -> Integration)
# -----------------------------------------------------------------------------

resource "aws_apigatewayv2_route" "ingest_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /ingest"
  target    = "integrations/${aws_apigatewayv2_integration.ingest_integration.id}"
}

resource "aws_apigatewayv2_route" "status_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /status"
  target    = "integrations/${aws_apigatewayv2_integration.status_integration.id}"
}

resource "aws_apigatewayv2_route" "history_route" {
  api_id    = aws_apigatewayv2_api.visionquest_api.id
  route_key = "POST /history" 
  target    = "integrations/${aws_apigatewayv2_integration.history_integration.id}"
}

# -----------------------------------------------------------------------------
# 5. Permissions (Allow API Gateway to Knock on the Lambda's Door)
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "api_gw_ingest" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_status" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_history" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.history_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visionquest_api.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# 6. Output (The URL)
# -----------------------------------------------------------------------------
output "api_url" {
  value = aws_apigatewayv2_stage.prod_stage.invoke_url
}
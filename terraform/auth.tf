# 1. USER POOL (The Directory of Users)
resource "aws_cognito_user_pool" "main_pool" {
  name = "VisionQuest_UserPool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
}

# 2. APP CLIENT (The "Door" for your Streamlit App)
resource "aws_cognito_user_pool_client" "streamlit_client" {
  name = "visionquest-frontend-client"

  user_pool_id = aws_cognito_user_pool.main_pool.id
  
  # Streamlit is a public client (web app), so we don't generate a secret
  generate_secret = false
  
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}

# OUTPUTS (You will need these for your frontend code)
output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main_pool.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.streamlit_client.id
}
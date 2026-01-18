# 1. THE STATE MACHINE ROLE
resource "aws_iam_role" "sfn_role" {
  name = "VisionQuest_Orchestrator_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
}

# 2. ALLOW SFN TO CALL LAMBDAS
resource "aws_iam_role_policy" "sfn_policy" {
  name = "VisionQuest_SFN_Permissions"
  role = aws_iam_role.sfn_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.ocr_cleaner.arn,
          aws_lambda_function.processor_lambda.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
            "dynamodb:UpdateItem", 
            "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.jobs_table.arn
      }
    ]
  })
}

# 3. THE STATE MACHINE DEFINITION
resource "aws_sfn_state_machine" "visionquest_pipeline" {
  name     = "VisionQuest-Orchestrator"
  role_arn = aws_iam_role.sfn_role.arn

  definition = <<EOF
{
  "Comment": "Orchestrates OCR -> Brain",
  "StartAt": "Agent: The Accountant (OCR)",
  "States": {
    "Agent: The Accountant (OCR)": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.ocr_cleaner.arn}",
      "Parameters": {
        "bucket.$": "$.bucket",
        "key.$": "$.key"
      },
      "ResultPath": "$.ocr_result",
      "Next": "Agent: The Brain (Bedrock)",
      "Retry": [ { "ErrorEquals": ["States.ALL"], "IntervalSeconds": 2, "MaxAttempts": 3 } ],
      "Catch": [ { "ErrorEquals": ["States.ALL"], "Next": "Job Failed" } ]
    },
    "Agent: The Brain (Bedrock)": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.processor_lambda.arn}",
      "Parameters": {
        "ocr_result.$": "$.ocr_result",
        "job_details.$": "$.job_details"
      },
      "Next": "Job Success",
      "Catch": [ { "ErrorEquals": ["States.ALL"], "Next": "Job Failed" } ]
    },
    "Job Success": {
      "Type": "Succeed"
    },
    "Job Failed": {
      "Type": "Fail",
      "Cause": "One of the agents crashed."
    }
  }
}
EOF
}
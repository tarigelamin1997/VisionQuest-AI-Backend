# -----------------------------------------------------------------------------
# 1. The Vector Database (OpenSearch Serverless)
# -----------------------------------------------------------------------------

locals {
  collection_name = "kb-${var.project_id}"
}

# A. Encryption Policy (Security)
resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "enc-${var.project_id}"
  type = "encryption"
  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${local.collection_name}"]
    }]
    AWSOwnedKey = true
  })
}

# B. Network Policy (Access)
resource "aws_opensearchserverless_security_policy" "network_policy" {
  name = "net-${var.project_id}"
  type = "network"
  policy = jsonencode([
    {
      Description = "Allow access to collection"
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${local.collection_name}"]
        },
        {
          ResourceType = "dashboard"
          Resource     = ["collection/${local.collection_name}"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# C. The Collection (The Database itself)
resource "aws_opensearchserverless_collection" "knowledge_vector_store" {
  name             = local.collection_name
  type             = "VECTORSEARCH"
  standby_replicas = "DISABLED"
  
  depends_on = [aws_opensearchserverless_security_policy.encryption_policy]
}

# -----------------------------------------------------------------------------
# 2. Permissions & DELAY
# -----------------------------------------------------------------------------

resource "aws_iam_role" "bedrock_kb_role" {
  name = "VisionQuest_Bedrock_KB_Role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_oss_policy" {
  name = "Bedrock_OpenSearch_Access"
  role = aws_iam_role.bedrock_kb_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["aoss:APIAccessAll"]
      Effect   = "Allow"
      Resource = aws_opensearchserverless_collection.knowledge_vector_store.arn
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_s3_policy" {
  name = "Bedrock_S3_Access"
  role = aws_iam_role.bedrock_kb_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Effect   = "Allow"
      Resource = [
        aws_s3_bucket.clean_knowledge.arn,
        "${aws_s3_bucket.clean_knowledge.arn}/*"
      ]
    }]
  })
}

# Allow the Role to use the Titan Embedding Model
resource "aws_iam_role_policy" "bedrock_model_policy" {
  name = "Bedrock_Model_Access"
  role = aws_iam_role.bedrock_kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
      }
    ]
  })
}


# D. Data Access Policy
resource "aws_opensearchserverless_access_policy" "data_access_policy" {
  name = "acl-${var.project_id}"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${local.collection_name}"]
          Permission   = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${local.collection_name}/*"]
          Permission   = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [aws_iam_role.bedrock_kb_role.arn, data.aws_caller_identity.current.arn]
    }
  ])
}

data "aws_caller_identity" "current" {}

# !!! CRITICAL FIX: The Buffer !!!
# This forces Terraform to just sit and wait for 60s after creating permissions.
resource "time_sleep" "wait_for_oss_propagation" {
  depends_on = [
    aws_opensearchserverless_collection.knowledge_vector_store,
    aws_opensearchserverless_access_policy.data_access_policy,
    aws_iam_role_policy.bedrock_oss_policy
  ]

  create_duration = "60s"
}

# -----------------------------------------------------------------------------
# 3. The Knowledge Base (The Librarian)
# -----------------------------------------------------------------------------

resource "aws_bedrockagent_knowledge_base" "main_kb" {
  name     = "VisionQuest-KB"
  role_arn = aws_iam_role.bedrock_kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.knowledge_vector_store.arn
      vector_index_name = "bedrock-knowledge-base-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  
  # Connect to the TIMER, not the resources directly
  depends_on = [time_sleep.wait_for_oss_propagation]
}

# -----------------------------------------------------------------------------
# 4. The Data Source
# -----------------------------------------------------------------------------

resource "aws_bedrockagent_data_source" "s3_source" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main_kb.id
  name              = "ZATCA-Regulations-Clean"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.clean_knowledge.arn
    }
  }
}

output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main_kb.id
}
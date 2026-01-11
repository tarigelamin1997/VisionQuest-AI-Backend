# -----------------------------------------------------------------------------
# 1. The Vault (VPC)
# -----------------------------------------------------------------------------
resource "aws_vpc" "visionquest_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "VisionQuest-VPC"
    Environment = "Production"
    Compliance  = "ZATCA-PDPL"
  }
}

# -----------------------------------------------------------------------------
# 2. The Private Rooms (Subnets for Lambdas & DB)
# We create two across different zones for "High Availability" (Resiliency).
# -----------------------------------------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.visionquest_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = { Name = "VisionQuest-Private-1" }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.visionquest_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = { Name = "VisionQuest-Private-2" }
}

# -----------------------------------------------------------------------------
# 3. The Security Guards (Security Groups)
# This is the firewall that wraps your Lambdas.
# -----------------------------------------------------------------------------
resource "aws_security_group" "lambda_sg" {
  name        = "visionquest-agent-sg"
  description = "Security Group for AI Agents (Textract/Llama)"
  vpc_id      = aws_vpc.visionquest_vpc.id

  # OUTBOUND: Allow Agents to talk to AWS Services (via Endpoints)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Only talk inside the Vault
  }

  tags = { Name = "VisionQuest-Agent-Firewall" }
}

# -----------------------------------------------------------------------------
# 4. The Secret Tunnels (VPC Endpoints)
# Critical for Compliance: Connect to S3 & Bedrock without touching the Internet.
# -----------------------------------------------------------------------------

# Gateway Endpoint for S3 (Free & Fast)
resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id       = aws_vpc.visionquest_vpc.id
  service_name = "com.amazonaws.us-east-1.s3" # Change region if needed
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_rt.id]
}

# Interface Endpoint for Bedrock Runtime (The Brain)
resource "aws_vpc_endpoint" "bedrock_endpoint" {
  vpc_id              = aws_vpc.visionquest_vpc.id
  service_name        = "com.amazonaws.us-east-1.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  security_group_ids  = [aws_security_group.lambda_sg.id]
  private_dns_enabled = true
}

# -----------------------------------------------------------------------------
# 5. Routing (The Map)
# Ensure traffic stays inside the private network.
# -----------------------------------------------------------------------------
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.visionquest_vpc.id

  tags = { Name = "VisionQuest-Private-Route" }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private_rt.id
}
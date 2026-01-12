import json
import boto3
import os

# --- CONFIGURATION ---
REGION = "us-east-1"
KB_ID = os.environ.get('KB_ID')
# We now accept the FULL ARN directly from Terraform
MODEL_ARN = os.environ.get('MODEL_ARN')

# --- CLIENT ---
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

def lambda_handler(event, context):
    print("Received Event:", json.dumps(event))
    
    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', 'What are the ZATCA regulations?')

        print(f"🧠 Querying KB: {KB_ID}")
        print(f"🤖 Using Model: {MODEL_ARN}")
        
        response = bedrock_runtime.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': MODEL_ARN # <--- Use the full ARN directly
                }
            }
        )
        
        answer = response['output']['text']
        citations = response.get('citations', [])
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "answer": answer,
                "citations": citations
            })
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
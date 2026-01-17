import json
import urllib.parse
import boto3
import os

# --- AWS CLIENTS ---
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime') # <--- The AI Engine

# --- CONFIGURATION (From compute.tf) ---
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
MODEL_ARN = os.environ.get('MODEL_ARN') #
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    print("🧠 Processor: Starting AI Analysis...")
    
    try:
        # 1. Validation & Extraction
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        job_id = key.split('/')[2]
        
        # 2. Update Status to PROCESSING
        update_job_status(job_id, 'PROCESSING')

        # 3. Get the User's Question from S3
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        input_data = json.loads(obj['Body'].read().decode('utf-8'))
        user_prompt = input_data.get('question', 'Please analyze the uploaded data.')

        # 4. CALL AI (Amazon Bedrock)
        print(f"🤖 Calling AI with prompt: {user_prompt[:50]}...")
        
        # Payload for Claude 3.5 Sonnet
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}]
                }
            ]
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ARN,
            body=json.dumps(payload)
        )
        
        result = json.loads(response['body'].read().decode('utf-8'))
        ai_answer = result['content'][0]['text']

        # 5. SAVE FINAL RESULT TO DYNAMODB
        print("✅ Analysis complete. Saving to database...")
        update_job_result(job_id, ai_answer)

        return {"status": "SUCCESS", "job_id": job_id}

    except Exception as e:
        print(f"❌ Processor Error: {str(e)}")
        if 'job_id' in locals():
            update_job_status(job_id, 'FAILED', str(e))
        return {"status": "ERROR", "message": str(e)}

# --- DATABASE HELPERS ---
def update_job_status(job_id, status, error=None):
    jobs_table.update_item(
        Key={'job_id': job_id},
        UpdateExpression="SET #s = :s" + (", error_msg = :e" if error else ""),
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':s': status, ':e': error} if error else {':s': status}
    )

def update_job_result(job_id, answer):
    jobs_table.update_item(
        Key={'job_id': job_id},
        UpdateExpression="SET #s = :s, answer = :a",
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':s': 'COMPLETED', ':a': answer}
    )
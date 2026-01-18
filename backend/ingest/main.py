import json
import boto3
import os
import uuid
import time
import base64

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Env Vars
BUCKET_NAME = os.environ.get('s3_bucket_name')
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    print("📥 Ingest: Received Request")
    
    try:
        # 1. Parse Input
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id', 'anonymous')
        chat_id = body.get('chat_id', 'default')
        file_name = body.get('file_name', 'upload.pdf')
        file_content_b64 = body.get('file_content') # Base64 string
        user_prompt = body.get('question', 'Analyze this.')

        if not file_content_b64:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No file content"})
            }

        # 2. Generate Ticket (Job ID)
        job_id = f"job-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        s3_key = f"{user_id}/{chat_id}/{job_id}/{file_name}"
        
        print(f"🎫 Created Job ID: {job_id}")

        # 3. Write "PROCESSING" to DynamoDB (CRITICAL STEP)
        jobs_table.put_item(Item={
            'job_id': job_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'status': 'PROCESSING',
            'created_at': int(time.time()),
            'file_name': file_name
        })
        print("✅ DB Entry Created")

        # 4. Upload to S3 (This triggers the Kickoff Lambda)
        # We upload a JSON wrapper to preserve the Prompt
        wrapper = {
            "question": user_prompt,
            "original_file_name": file_name,
            # We don't necessarily need the base64 here if we upload the raw file, 
            # BUT for the 'Kickoff' logic we wrote earlier, let's stick to the raw file 
            # OR the wrapper. 
            # FIX: We will upload the RAW PDF to S3 so Textract works natively.
            # We will store the Prompt in DynamoDB (already done in step 3? No, let's add it).
        }
        
        # Update DB with prompt
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET user_prompt = :p",
            ExpressionAttributeValues={':p': user_prompt}
        )

        # Decode and Upload Raw PDF (Better for Textract)
        file_bytes = base64.b64decode(file_content_b64)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType='application/pdf'
        )
        print(f"🚀 Uploaded to S3: {s3_key}")

        return {
            "statusCode": 200,
            "body": json.dumps({"job_id": job_id, "message": "Upload successful"})
        }

    except Exception as e:
        print(f"❌ Ingest Failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
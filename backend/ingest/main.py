import json
import boto3
import uuid
import base64
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    """
    THE RECEPTIONIST
    1. Accepts Audio/Image/Text
    2. Saves to S3 (This triggers the Processor)
    3. Creates a 'Ticket' (Job ID) in DynamoDB
    4. Returns Job ID to user immediately
    """
    print("📨 Ingest: Request Received")
    
    try:
        # 1. Parse Request
        body = json.loads(event.get('body', '{}'))
        
        # User Data (In the future, this comes from Cognito Token)
        user_id = body.get('user_id', 'guest_user') 
        chat_id = body.get('chat_id', 'default_chat')
        
        # Generate the Ticket
        job_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # 2. Determine Data Type (Audio vs Image vs Text)
        s3_key = ""
        job_type = "text"
        
        if 'audio' in body:
            job_type = "audio"
            file_data = base64.b64decode(body['audio'])
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.webm"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_data)
            print(f"🎙️ Audio saved to: {s3_key}")

        elif 'file_data' in body:
            job_type = "document" # PDF or Image
            file_data = base64.b64decode(body['file_data'])
            extension = body.get('file_name', 'doc').split('.')[-1]
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.{extension}"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_data)
            print(f"jq Document saved to: {s3_key}")
            
        else:
            # Pure Text Chat
            job_type = "text"
            # For text, we might still save a JSON to S3 to trigger the processor standardly
            # OR just trigger the logic via DynamoDB stream. 
            # For simplicity in V1, let's save the text as a JSON file to S3 to trigger the same pipeline.
            payload = json.dumps({"question": body.get('question')})
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.json"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=payload)

        # 3. Issue the Ticket (DynamoDB)
        # We save the job details so the Status Lambda can check it later
        jobs_table.put_item(Item={
            'job_id': job_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'status': 'PENDING',
            'type': job_type,
            's3_input_key': s3_key,
            'created_at': timestamp,
            'expiration_time': timestamp + 86400 # Auto-delete after 24h
        })

        # 4. Return the Ticket
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "job_id": job_id,
                "status": "PENDING",
                "message": "Request accepted. Processing started."
            })
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
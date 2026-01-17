import json
import boto3
import uuid
import base64
import os
import time

# --- CLIENTS ---
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# --- CONFIGURATION ---
BUCKET_NAME = os.environ.get('BUCKET_NAME')
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
CHATS_TABLE_NAME = os.environ.get('CHATS_TABLE_NAME')

jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
chats_table = dynamodb.Table(CHATS_TABLE_NAME)

def lambda_handler(event, context):
    """
    RECEIVES: POST /submit (with file/audio/text)
    OR: GET /test (for health check)
    """
    print("📨 Ingest: Request Received")
    
    try:
        # 1. Handle Empty Body (Browser tests or GET requests)
        raw_body = event.get('body')
        if not raw_body:
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "alive", "message": "VisionQuest Ingest is ready for data!"})
            }

        # 2. Parse Incoming JSON
        body = json.loads(raw_body)
        user_id = body.get('user_id', 'guest')
        chat_id = body.get('chat_id', str(uuid.uuid4()))
        question_text = body.get('question', '')
        
        job_id = str(uuid.uuid4())
        timestamp = int(time.time())
        s3_key = ""
        job_type = "text"
        preview = question_text[:50] if question_text else "New Conversation"

        # 3. Route to S3 based on Data Type
        if 'audio' in body:
            job_type = "audio"
            file_data = base64.b64decode(body['audio'])
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.webm"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_data)
            preview = "🎤 Audio Message"

        elif 'file_data' in body:
            job_type = "document"
            file_data = base64.b64decode(body['file_data'])
            file_name = body.get('file_name', 'upload.pdf')
            ext = file_name.split('.')[-1]
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.{ext}"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_data)
            preview = f"📄 {file_name}"
            
        else:
            # Standard Text Chat
            job_type = "text"
            payload = json.dumps({"question": question_text})
            s3_key = f"{user_id}/{chat_id}/{job_id}/input.json"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=payload)

        # 4. Save Chat Metadata (For Sidebar History)
        chats_table.update_item(
            Key={'user_id': user_id, 'chat_id': chat_id},
            UpdateExpression="SET title = if_not_exists(title, :t), last_active = :l",
            ExpressionAttributeValues={':t': preview, ':l': timestamp}
        )

        # 5. Create Job Ticket (Triggers Processor via S3 Event)
        jobs_table.put_item(Item={
            'job_id': job_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'status': 'PENDING',
            'type': job_type,
            'created_at': timestamp,
            'expiration_time': timestamp + 86400 # 24hr TTL
        })

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"job_id": job_id, "chat_id": chat_id})
        }

    except Exception as e:
        print(f"❌ Ingest Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
import json
import boto3
import os

# --- CONFIGURATION ---
dynamodb = boto3.resource('dynamodb')
# Matches the variable passed in compute.tf [cite: 15]
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    print("📡 Status Check: Received Request")
    
    try:
        # 1. Parse the request body
        body = json.loads(event.get('body', '{}'))
        job_id = body.get('job_id')
        
        if not job_id:
            print("❌ Error: Missing job_id in request")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing job_id"})
            }

        # 2. Fetch the current state from DynamoDB [cite: 15]
        print(f"🔍 Looking up Job: {job_id}")
        response = jobs_table.get_item(Key={'job_id': job_id})
        item = response.get('Item')

        if not item:
            print(f"⚠️ Job {job_id} not found in database")
            return {
                "statusCode": 404,
                "body": json.dumps({"status": "NOT_FOUND"})
            }

        # 3. Return the full job ticket (status, answer, etc.)
        print(f"✅ Status Found: {item.get('status')}")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(item)
        }

    except Exception as e:
        print(f"❌ Status Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
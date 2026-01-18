import json
import boto3
import os
from decimal import Decimal

# --- THE TRANSLATOR (Fixes the JSON Error) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to int if it's a whole number, else float
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

# --- CONFIGURATION ---
dynamodb = boto3.resource('dynamodb')
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    print("📡 Status Check: Received Request")
    
    # CORS HEADERS (Critical for Browser Access)
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json"
    }

    try:
        # 1. Parse Input
        body = json.loads(event.get('body', '{}'))
        job_id = body.get('job_id')
        
        if not job_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Missing job_id"})
            }

        # 2. Fetch from DynamoDB
        print(f"🔍 Looking up Job: {job_id}")
        response = jobs_table.get_item(Key={'job_id': job_id})
        item = response.get('Item')

        if not item:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"status": "NOT_FOUND"})
            }

        print(f"✅ Status Found: {item.get('status')}")

        # 3. Return Response (USING THE TRANSLATOR)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(item, cls=DecimalEncoder) # <--- THE FIX
        }

    except Exception as e:
        print(f"❌ Status Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
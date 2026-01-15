import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
JOBS_TABLE = dynamodb.Table(os.environ['JOBS_TABLE_NAME'])

# Helper to fix JSON serialization of Decimal (DynamoDB quirk)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        # Parse Job ID from query string (GET /status?job_id=123)
        # Note: API Gateway HTTP API puts query params in 'queryStringParameters'
        params = event.get('queryStringParameters', {})
        job_id = params.get('job_id')
        
        if not job_id:
            # Try body if it's a POST
            body = json.loads(event.get('body', '{}'))
            job_id = body.get('job_id')

        if not job_id:
            return {"statusCode": 400, "body": "Missing job_id"}

        # Fetch from DynamoDB
        response = JOBS_TABLE.get_item(Key={'job_id': job_id})
        
        if 'Item' not in response:
            return {"statusCode": 404, "body": json.dumps({"status": "NOT_FOUND"})}
            
        item = response['Item']
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(item, cls=DecimalEncoder)
        }

    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# --- CONFIGURATION ---
dynamodb = boto3.resource('dynamodb')
JOBS_TABLE = dynamodb.Table(os.environ['JOBS_TABLE_NAME'])
CHATS_TABLE = dynamodb.Table(os.environ['CHATS_TABLE_NAME'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """
    THE HISTORIAN
    1. GET /history?user_id=...&chat_id=... -> Returns messages for one chat
    2. GET /history/list?user_id=...       -> Returns list of all user's chats
    """
    print(event)
    
    # 1. Parse Query Params
    params = event.get('queryStringParameters', {})
    if not params:
        return {"statusCode": 400, "body": "Missing parameters"}
    
    user_id = params.get('user_id')
    chat_id = params.get('chat_id')
    action = params.get('action', 'fetch_messages') # 'fetch_messages' or 'list_chats'

    try:
        # --- ACTION A: LIST PREVIOUS CHATS ---
        if action == 'list_chats':
            response = CHATS_TABLE.query(
                KeyConditionExpression=Key('user_id').eq(user_id)
            )
            chats = response.get('Items', [])
            return {
                "statusCode": 200,
                "body": json.dumps(chats, cls=DecimalEncoder)
            }

        # --- ACTION B: FETCH MESSAGES FOR A CHAT ---
        if chat_id:
            # Query the GSI 'ChatIndex' we just created
            response = JOBS_TABLE.query(
                IndexName='ChatIndex',
                KeyConditionExpression=Key('chat_id').eq(chat_id)
            )
            messages = response.get('Items', [])
            
            # Sort by created_at just in case
            messages.sort(key=lambda x: x.get('created_at', 0))

            return {
                "statusCode": 200,
                "body": json.dumps(messages, cls=DecimalEncoder)
            }
            
        return {"statusCode": 400, "body": "Invalid Request"}

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": str(e)}
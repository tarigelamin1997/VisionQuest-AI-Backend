import boto3
import uuid
import json
import urllib.parse
from datetime import datetime

# --- CONFIGURATION ---
REGION = "us-east-1"
DYNAMO_TABLE = "VisionQuest_Ingestion_Logs"

# --- CLIENTS ---
s3 = boto3.client("s3", region_name=REGION)
translate = boto3.client("translate", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMO_TABLE)

def log_status(file_id, filename, status, details=None):
    print(f"📝 [LOG] {filename}: {status}")
    try:
        table.put_item(
            Item={
                'FileID': file_id,
                'Filename': filename,
                'Status': status,
                'Timestamp': str(datetime.now()),
                'Details': details or "N/A"
            }
        )
    except Exception as e:
        print(f"⚠️ DynamoDB Error: {e}")

def process_file(bucket, key):
    """
    The Core Logic: Download -> Detect -> Translate -> Upload
    """
    filename = key.split('/')[-1]
    file_id = str(uuid.uuid4())
    log_status(file_id, filename, "STARTED")

    try:
        # 1. EXTRACT
        print(f"⬇️ Downloading {key}...")
        response = s3.get_object(Bucket=bucket, Key=key)
        raw_text = response['Body'].read().decode('utf-8')

        # 2. TRANSFORM
        # Check first 100 chars for Arabic
        is_arabic = any("\u0600" <= c <= "\u06FF" for c in raw_text[:100])
        
        if is_arabic:
            source, target = "ar", "en"
            print("🌍 Detected Arabic -> Translating to English")
        else:
            source, target = "en", "ar"
            print("🌍 Detected English -> Translating to Arabic")

        # Call AWS Translate
        result = translate.translate_text(
            Text=raw_text[:5000], # Limit for demo
            SourceLanguageCode=source,
            TargetLanguageCode=target
        )
        translated_text = result.get('TranslatedText')

        # 3. LOAD
        new_key = f"processed/{target}/{filename}"
        s3.put_object(
            Bucket=bucket,
            Key=new_key,
            Body=translated_text.encode('utf-8')
        )
        
        log_status(file_id, filename, "COMPLETED", f"Translated {source}->{target}")
        return True

    except Exception as e:
        log_status(file_id, filename, "FAILED", str(e))
        print(f"❌ Error: {e}")
        raise e # Raise so SQS knows to retry

def handler(event, context):
    """
    THE LISTENER: Unwraps SQS messages and triggers processing.
    """
    print("⚡ Lambda Handler Triggered")
    
    # Loop through SQS Messages
    for record in event['Records']:
        try:
            # SQS wraps the S3 Event inside the 'body' string
            s3_event = json.loads(record['body'])
            
            # Now loop through S3 Records inside that
            if 'Records' in s3_event:
                for s3_record in s3_event['Records']:
                    bucket = s3_record['s3']['bucket']['name']
                    # Decode URL (e.g., 'file%20name.txt' -> 'file name.txt')
                    key = urllib.parse.unquote_plus(s3_record['s3']['object']['key'])
                    
                    print(f"📨 Processing Event for: {key}")
                    process_file(bucket, key)
            else:
                print("⚠️ No S3 records found in SQS message (Test Event?)")
                
        except Exception as e:
            print(f"💥 Handler Error: {e}")
            raise e # Triggers DLQ Logic
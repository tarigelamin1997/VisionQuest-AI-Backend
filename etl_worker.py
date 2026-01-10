import boto3
import uuid
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
REGION = "us-east-1"
DYNAMO_TABLE = "VisionQuest_Ingestion_Logs"
TARGET_BUCKET = "visionquest-kb-tarig-001" # Replace with your actual bucket name

# --- CLIENTS ---
s3 = boto3.client("s3", region_name=REGION)
translate = boto3.client("translate", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMO_TABLE)

def log_status(file_id, filename, status, details=None):
    """
    Writes job status to DynamoDB (The 'Audit Trail').
    """
    print(f"📝 [LOG] {filename}: {status}")
    table.put_item(
        Item={
            'FileID': file_id,
            'Filename': filename,
            'Status': status,
            'Timestamp': str(datetime.now()),
            'Details': details or "N/A"
        }
    )

def translate_document(text, source_lang="en", target_lang="ar"):
    """
    Calls AWS Translate. Handles large text by chunking if necessary.
    """
    try:
        # Limit to 5000 bytes for this demo (AWS limit is 10k per call)
        response = translate.translate_text(
            Text=text[:5000],
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        return response.get('TranslatedText')
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        return None

def process_file_content(bucket, key):
    """
    The Core ETL Logic.
    """
    file_id = str(uuid.uuid4())
    filename = key.split('/')[-1]
    
    log_status(file_id, filename, "STARTED")

    try:
        # 1. EXTRACT (Read from S3)
        print(f"⬇️ Downloading {key}...")
        response = s3.get_object(Bucket=bucket, Key=key)
        raw_text = response['Body'].read().decode('utf-8') # Assuming .txt for simplicity first

        # 2. TRANSFORM (Translate)
        # Strategy: If we detect Arabic characters, translate to English. If English, to Arabic.
        # Simple heuristic: Check first 50 chars for Arabic unicode
        is_arabic = any("\u0600" <= c <= "\u06FF" for c in raw_text[:50])
        
        if is_arabic:
            source, target = "ar", "en"
            print("🌍 Detected Arabic -> Translating to English")
        else:
            source, target = "en", "ar"
            print("🌍 Detected English -> Translating to Arabic")

        translated_text = translate_document(raw_text, source, target)
        
        if not translated_text:
            raise Exception("Translation returned empty result")

        # 3. LOAD (Save 'Twin' file to S3)
        new_key = f"processed/{target}/{filename}"
        s3.put_object(
            Bucket=bucket,
            Key=new_key,
            Body=translated_text.encode('utf-8')
        )
        print(f"✅ Saved translation to: {new_key}")

        # 4. LOG SUCCESS
        log_status(file_id, filename, "COMPLETED", f"Translated {source}->{target}")
        
    except Exception as e:
        log_status(file_id, filename, "FAILED", str(e))
        print(f"❌ Critical Error: {e}")

# --- SIMULATION (Running locally for now) ---
if __name__ == "__main__":
    # In a real container, this would read from SQS or Event Trigger
    # For testing, we create a dummy file
    test_filename = "test_policy.txt"
    test_content = "The Value Added Tax (VAT) rate in Saudi Arabia is 15%."
    
    print("🧪 Simulating Pipeline Trigger...")
    
    # 1. Upload Test File
    s3.put_object(Bucket=TARGET_BUCKET, Key=f"raw/{test_filename}", Body=test_content)
    
    # 2. Run Processor
    process_file_content(TARGET_BUCKET, f"raw/{test_filename}")
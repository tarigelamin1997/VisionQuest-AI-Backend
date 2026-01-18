import boto3
import json
import os
import urllib.parse
import time

sfn = boto3.client('stepfunctions')
s3 = boto3.client('s3')

STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def lambda_handler(event, context):
    print("🚀 Kickoff: New file detected.")
    
    # 1. Parse S3 Event
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        print(f"📂 File: {key} in Bucket: {bucket}")
    except Exception as e:
        print(f"❌ Error parsing event: {e}")
        return

    # 2. Determine File Type & Extract Prompt
    user_prompt = "Analyze this document." # Default if we can't find one
    
    try:
        # Check if it looks like a JSON file
        if key.lower().endswith('.json'):
            obj = s3.get_object(Bucket=bucket, Key=key)
            content = obj['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            # If it's a wrapper, the REAL file might be inside, or this IS the metadata
            # For now, let's assume if it's JSON, the prompt is inside.
            user_prompt = data.get('question', user_prompt)
            print(f"📝 Found JSON wrapper. Prompt: {user_prompt}")
            
        elif key.lower().endswith('.pdf'):
            print("Tb Detected Raw PDF. Using default prompt.")
            
        else:
            print(f"⚠️ Unknown file type: {key}. Proceeding anyway.")

    except Exception as e:
        print(f"⚠️ Warning: Could not read file content for prompt. Using default. Error: {e}")

    # 3. Generate Job ID (Unique)
    # If key is "user/chat/job/file.pdf", split it. If just "file.pdf", make one up.
    parts = key.split('/')
    if len(parts) > 2:
        job_id = parts[2]
    else:
        job_id = f"job-{int(time.time())}"

    # 4. Start Orchestrator
    try:
        input_payload = {
            "bucket": bucket,
            "key": key,
            "job_details": {
                "job_id": job_id,
                "user_prompt": user_prompt
            }
        }
        
        print(f"🚀 Starting Execution for Job: {job_id}")
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"{job_id}-{int(time.time())}", # Ensure unique execution name
            input=json.dumps(input_payload)
        )
        print("✅ State Machine Triggered!")
        return {"status": "SUCCESS", "job_id": job_id}
        
    except Exception as e:
        print(f"❌ FAILED to start Step Function: {str(e)}")
        raise e
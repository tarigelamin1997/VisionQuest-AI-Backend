import boto3
import urllib.parse
import json
import time
import os

textract = boto3.client('textract')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    print(f"🧹 OCR Agent Started. Input: {json.dumps(event)}")
    
    # 1. Unpack Direct Input
    bucket = event.get('bucket')
    key = event.get('key')
    
    if not bucket or not key:
        raise ValueError("Missing 'bucket' or 'key' in input")

    print(f"🔍 Analyzing document: {key}")

    try:
        # --- PATH A: IMAGE (JPG/PNG) - Fast & Synchronous ---
        if key.lower().endswith(('.png', '.jpg', '.jpeg')):
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}}
            )
            return extract_text_from_blocks(response['Blocks'], bucket, key)

        # --- PATH B: PDF - Async & Polling ---
        elif key.lower().endswith('.pdf'):
            # 1. Start the Job
            start_response = textract.start_document_text_detection(
                DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}}
            )
            job_id = start_response['JobId']
            print(f"⏳ PDF Detected. Async Job Started: {job_id}")

            # 2. Poll for Completion (Wait loop)
            status = "IN_PROGRESS"
            while status == "IN_PROGRESS":
                time.sleep(2) # Wait 2 seconds
                job_status = textract.get_document_text_detection(JobId=job_id)
                status = job_status['JobStatus']
                
                if status == "FAILED":
                    raise Exception(f"Textract Job Failed: {job_status}")
            
            # 3. Job Done - Get Results
            print("✅ PDF Processing Complete.")
            
            # Note: Pagination logic is needed for massive PDFs, 
            # but for <50 pages, this usually grabs the bulk.
            return extract_text_from_blocks(job_status['Blocks'], bucket, key)

        else:
            raise ValueError(f"Unsupported file format: {key}")

    except Exception as e:
        print(f"❌ OCR Failed: {str(e)}")
        raise e 

def extract_text_from_blocks(blocks, bucket, key):
    extracted_text = ""
    for item in blocks:
        if item['BlockType'] == 'LINE':
            extracted_text += item['Text'] + "\n"
            
    return {
        "status": "SUCCESS",
        "bucket": bucket,
        "key": key,
        "extracted_text": extracted_text
    }
import boto3
import os
import urllib.parse
import json

s3 = boto3.client('s3')
textract = boto3.client('textract')

def lambda_handler(event, context):
    # 1. Get the uploaded file details
    bucket_in = event['Records'][0]['s3']['bucket']['name']
    file_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    bucket_out = os.environ['CLEAN_BUCKET']
    
    print(f"🧹 OCR Job Started for: {file_key}")

    try:
        # 2. Call Textract (Uses VPC Endpoint automatically)
        # Note: For large PDFs (>1 page), we should use start_document_text_detection (Async).
        # For this Phase B MVP, we use synchronous detect_document_text for speed on single pages/images.
        # If you upload a 50-page PDF, this specific call might verify only the first page or need async logic.
        
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': bucket_in, 'Name': file_key}}
        )

        # 3. Extract Text (Preserving Order)
        extracted_text = ""
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                extracted_text += item['Text'] + "\n"

        # 4. Save Clean Text
        clean_key = file_key.rsplit('.', 1)[0] + ".txt"
        
        s3.put_object(
            Bucket=bucket_out,
            Key=clean_key,
            Body=extracted_text
        )
        
        print(f"✅ Success! Clean text saved to: {bucket_out}/{clean_key}")
        return {"status": "success", "file": clean_key}

    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")
        raise e
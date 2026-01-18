import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME')
MODEL_ARN = os.environ.get('MODEL_ARN')
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)

def lambda_handler(event, context):
    print("🧠 Brain Activated.")
    
    # 1. Unpack Input (From OCR Step)
    # The Step Function passes the output of OCR as 'ocr_result'
    try:
        ocr_result = event.get('ocr_result', {})
        extracted_text = ocr_result.get('extracted_text', "")
        
        # Metadata passed through from the start
        job_details = event.get('job_details', {})
        job_id = job_details.get('job_id')
        user_prompt = job_details.get('user_prompt', "Analyze this document.")
        
        if not job_id:
            raise ValueError("Job ID missing from event payload")

        print(f"⚙️ Processing Job: {job_id}")

        # 2. Construct Prompt
        final_prompt = f"""
        You are an expert AI Data Analyst for Saudi SMEs.
        User Question: {user_prompt}
        
        Document Context:
        {extracted_text}
        
        Provide a professional, concise answer in Arabic (unless asked otherwise).
        """

        # 3. Call Bedrock (Claude 3.5 Sonnet)
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": final_prompt}]}
            ]
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ARN,
            body=json.dumps(payload)
        )
        
        result = json.loads(response['body'].read().decode('utf-8'))
        ai_answer = result['content'][0]['text']

        # 4. The Scribe (Write to DB)
        print("✅ Analysis complete. Saving to DynamoDB...")
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :s, answer = :a",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'SUCCESS', ':a': ai_answer}
        )

        return {"status": "SUCCESS", "job_id": job_id}

    except Exception as e:
        print(f"❌ Processor Error: {str(e)}")
        if 'job_id' in locals() and job_id:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression="SET #s = :s, error_msg = :e",
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'FAILED', ':e': str(e)}
            )
        raise e
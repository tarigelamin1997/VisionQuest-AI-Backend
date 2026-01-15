import json
import urllib.parse
import boto3
import os
import time
import base64

# --- CLIENTS ---
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# --- CONFIGURATION ---
JOBS_TABLE = dynamodb.Table(os.environ['JOBS_TABLE_NAME'])
KB_ID = os.environ['KB_ID']
MODEL_ARN = os.environ['MODEL_ARN']

def lambda_handler(event, context):
    """
    THE WORKER (Async)
    1. Triggered by S3 Upload
    2. Identifies file type (Audio vs Image vs Text vs PDF)
    3. Runs AI Process
    4. Updates DynamoDB with the Final Answer
    """
    print("⚙️ Processor: Job Triggered")
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # Extract Job ID: user_id/chat_id/job_id/filename
    parts = key.split('/')
    if len(parts) < 3:
        print("❌ Invalid S3 Key structure")
        return
        
    job_id = parts[2]
    print(f"🆔 Processing Job: {job_id} | Key: {key}")

    try:
        update_job_status(job_id, 'PROCESSING')

        result_text = ""
        citations = []

        # --- ROUTING LOGIC ---
        if key.endswith('.webm') or key.endswith('.mp3') or key.endswith('.wav'):
            print("🎙️ Mode: Audio Processing")
            transcript = process_audio(bucket, key, job_id)
            # Chain: Transcript -> RAG
            rag_response = query_bedrock_rag(transcript)
            result_text = rag_response['output']['text']
            citations = rag_response['citations']

        elif key.endswith('.png') or key.endswith('.jpg') or key.endswith('.jpeg'):
            print("👁️ Mode: Vision Analysis")
            result_text = process_image(bucket, key)
            
        elif key.endswith('.pdf'):
            print("📄 Mode: Document Analysis")
            # NOW ACTIVE: Sends PDF to Bedrock
            result_text = process_pdf(bucket, key)
            
        elif key.endswith('.json'):
            print("💬 Mode: Text Chat")
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            data = json.loads(obj['Body'].read())
            question = data.get('question')
            
            rag_response = query_bedrock_rag(question)
            result_text = rag_response['output']['text']
            citations = rag_response['citations']

        # --- SAVE RESULT ---
        update_job_result(job_id, result_text, citations)
        print("✅ Job Completed Successfully")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        update_job_status(job_id, 'FAILED', str(e))
        raise e

    return {"status": "success"}

# --- HELPER FUNCTIONS ---

def process_audio(bucket, key, job_id):
    """Transcribes Audio"""
    job_name = f"job_{job_id}_{int(time.time())}"
    media_uri = f"s3://{bucket}/{key}"
    
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': media_uri},
        MediaFormat='webm',
        LanguageCode='ar-SA' # Defaulting to Arabic/Saudi
    )
    
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status['TranscriptionJob']['TranscriptionJobStatus']
        if job_status in ['COMPLETED', 'FAILED']:
            break
        time.sleep(1)
        
    if job_status == 'COMPLETED':
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        import urllib.request
        with urllib.request.urlopen(transcript_uri) as response:
            data = json.loads(response.read())
            return data['results']['transcripts'][0]['transcript']
    else:
        raise Exception("Transcription Failed")

def process_image(bucket, key):
    """Analyzes Images with Claude 3.5"""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    b64_image = base64.b64encode(response['Body'].read()).decode('utf-8')
    
    prompt = "Describe this image in detail. If it's a document, extract the key information."
    
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_image}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }
    
    response = bedrock_runtime.invoke_model(modelId=MODEL_ARN, body=json.dumps(payload))
    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def process_pdf(bucket, key):
    """Analyzes PDFs with Claude 3.5 (Document API)"""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    b64_pdf = base64.b64encode(response['Body'].read()).decode('utf-8')
    
    prompt = "Analyze this document. Summarize its purpose and extract any specific dates, amounts, or names."
    
    # Claude 3 supports PDF blocks directly
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64_pdf
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }
    
    response = bedrock_runtime.invoke_model(modelId=MODEL_ARN, body=json.dumps(payload))
    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def query_bedrock_rag(query):
    """Queries Knowledge Base"""
    # Note: If query is empty/short, Bedrock might error. Safe guard:
    if not query or len(query) < 2: return {'output': {'text': "No clear input detected."}, 'citations': []}

    response = bedrock_agent_runtime.retrieve_and_generate(
        input={'text': query},
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': KB_ID,
                'modelArn': MODEL_ARN
            }
        }
    )
    return response

def update_job_status(job_id, status, error_msg=None):
    update_expr = "SET #s = :s"
    expr_attr_values = {':s': status}
    
    if error_msg:
        update_expr += ", error_msg = :e"
        expr_attr_values[':e'] = error_msg

    JOBS_TABLE.update_item(
        Key={'job_id': job_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues=expr_attr_values
    )

def update_job_result(job_id, answer, citations):
    JOBS_TABLE.update_item(
        Key={'job_id': job_id},
        UpdateExpression="SET #s = :s, answer = :a, citations = :c",
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':s': 'COMPLETED', ':a': answer, ':c': citations}
    )
import json
import boto3
import os
import base64
import time
import uuid
import urllib.request

# --- CONFIGURATION ---
REGION = "us-east-1"
KB_ID = os.environ.get('KB_ID')
MODEL_ARN = os.environ.get('MODEL_ARN')
BUCKET_NAME = os.environ.get('BUCKET_NAME')

# --- CLIENTS ---
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)
transcribe = boto3.client('transcribe', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

def transcribe_audio(base64_audio):
    """
    Uploads audio to S3, starts a Transcribe job, polls for completion, returns text.
    """
    job_name = f"voice_query_{uuid.uuid4()}"
    file_name = f"audio_temp/{job_name}.webm"
    
    # 1. Decode and Upload to S3
    print(f"🎙️ Uploading audio to {BUCKET_NAME}/{file_name}")
    audio_data = base64.b64decode(base64_audio)
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=audio_data)
    
    media_uri = f"s3://{BUCKET_NAME}/{file_name}"
    
    # 2. Start Transcription Job
    print(f"⏳ Starting Transcribe Job: {job_name}")
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': media_uri},
        MediaFormat='webm',
        LanguageCode='ar-SA' 
    )
    
    # 3. Poll for Completion (FASTER LOOP)
    max_retries = 60 # wait max 12-15 seconds
    while max_retries > 0:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status['TranscriptionJob']['TranscriptionJobStatus']
        
        if job_status in ['COMPLETED', 'FAILED']:
            break
        
        # KEY CHANGE: Check every 0.2 seconds instead of 1.0
        time.sleep(0.2) 
        max_retries -= 1
        
    if job_status == 'COMPLETED':
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        with urllib.request.urlopen(transcript_uri) as response:
            data = json.loads(response.read())
            text = data['results']['transcripts'][0]['transcript']
            print(f"✅ Transcribed: {text}")
            return text
    else:
        print("❌ Transcription Failed or Timed Out")
        return None

def analyze_media_with_rag(question, base64_data, media_type):
    """
    Handles BOTH Images (Vision) and PDFs (Document API).
    """
    print(f"📂 Processing Media: {media_type}")
    
    # 1. Retrieve Rules from KB
    retrieval = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={'text': question}
    )
    
    context_text = ""
    citations_list = []
    if 'retrievalResults' in retrieval:
        for result in retrieval['retrievalResults']:
            text_chunk = result['content']['text']
            uri = result['location']['s3Location']['uri']
            context_text += f"- {text_chunk}\n"
            citations_list.append({'retrievedReferences': [{'content': {'text': text_chunk}, 'location': {'s3Location': {'uri': uri}}}]})

    # 2. Prepare Payload based on Type
    # PDF uses "document" block. Images use "image" block.
    content_block = {}
    
    if "pdf" in media_type:
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf", 
                "data": base64_data
            }
        }
    else:
        # Assume Image (jpeg/png)
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type, # e.g. "image/png"
                "data": base64_data
            }
        }

    prompt_text = f"""
    You are an expert ZATCA Consultant.
    Review the provided document/image and answer the user's question.
    
    OFFICIAL REGULATIONS context:
    {context_text}
    
    User Question: {question}
    """

    # 3. Call Claude
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096, # Increased for PDF reading
        "messages": [
            {
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]
    }

    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ARN,
        body=json.dumps(payload)
    )
    
    result = json.loads(response['body'].read())
    return result['content'][0]['text'], citations_list

def lambda_handler(event, context):
    print("Received Event:", json.dumps(event))
    
    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question')
        audio_data = body.get('audio')
        file_data = body.get('file_data') # Unified file field
        media_type = body.get('media_type') # e.g. "application/pdf"
        
        # 1. Voice Handling
        if audio_data:
            transcribed_text = transcribe_audio(audio_data)
            if not transcribed_text: return {"statusCode": 500, "body": json.dumps({"error": "Transcription failed"})}
            question = transcribed_text 

        if not question and not file_data:
            return {"statusCode": 400, "body": json.dumps({"error": "No input provided"})}

        # 2. File Handling (PDF or Image)
        if file_data and media_type:
            if not question: question = "Analyze this file."
            answer, citations = analyze_media_with_rag(question, file_data, media_type)
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "answer": answer,
                    "citations": citations,
                    "transcribed_text": question if audio_data else None
                })
            }

        # 3. Text Handling (Standard)
        print(f"🧠 Text Mode: '{question}'")
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': MODEL_ARN
                }
            }
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "answer": response['output']['text'],
                "citations": response.get('citations', []),
                "transcribed_text": question if audio_data else None
            })
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
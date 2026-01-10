import boto3
import json

# --- CONFIGURATION ---
KB_ID = "ND3AZR5QZN" 
# Text Model (Llama 3 8B) - Fast & Cheap for chat
TEXT_MODEL_ID = "meta.llama3-8b-instruct-v1:0"
# Vision Model (Llama 3.2 11B) - Smart & Multimodal for images
VISION_MODEL_ID = "meta.llama3-2-11b-instruct-v1:0" 
REGION = "us-east-1"

# 1. Setup Clients
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

def retrieve_from_kb(query):
    """
    Step 1: Ask the Librarian (Knowledge Base) for relevant pages.
    """
    print(f"🔎 Scanning Knowledge Base for: '{query}'...")
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': 3}
            }
        )
        return response.get('retrievalResults', [])
    except Exception as e:
        print(f"❌ Retrieval Error: {str(e)}")
        return []

def generate_answer(query, retrieved_docs, language="English"):
    """
    Step 2: Send Text Context to Llama 3 (Text Model).
    """
    if not retrieved_docs:
        return "Sorry, I couldn't find any documents to answer that."

    context_text = ""
    for doc in retrieved_docs:
        context_text += f"{doc['content']['text']}\n"

    system_instruction = f"You are an expert on Saudi ZATCA regulations. Answer in {language}."
    
    formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_instruction}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Context: {context_text}
Question: {query}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    body = json.dumps({
        "prompt": formatted_prompt,
        "max_gen_len": 512,
        "temperature": 0.5,
        "top_p": 0.9
    })

    try:
        response = bedrock_runtime.invoke_model(modelId=TEXT_MODEL_ID, body=body)
        response_body = json.loads(response.get("body").read())
        return response_body['generation']
    except Exception as e:
        return f"❌ Text Generation Error: {str(e)}"

def analyze_invoice_image(image_bytes, language="English"):
    """
    Step 3: The 'Inspector' - Sends Image to Llama 3.2 Vision.
    """
    print("🕵️‍♂️ Inspecting Invoice Image...")
    
    # Prompt for the Vision Model
    prompt_text = f"Analyze this image carefully. Is this a valid invoice according to KSA ZATCA regulations? Check for: QR Code, VAT Number, Date, and Total Amount. Answer in {language}."

    # Using the Bedrock 'Converse' API (Best for Vision)
    messages = [
        {
            "role": "user",
            "content": [
                {"image": {"format": "png", "source": {"bytes": image_bytes}}}, # Llama accepts PNG/JPEG bytes directly
                {"text": prompt_text}
            ]
        }
    ]

    try:
        response = bedrock_runtime.converse(
            modelId=VISION_MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 512, "temperature": 0.1}
        )
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        return f"❌ Vision Error: {str(e)}"
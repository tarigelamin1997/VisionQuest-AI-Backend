import boto3
import json

# --- CONFIGURATION ---
KB_ID = "ND3AZR5QZN"
# We use Llama 3 (Found in your scan list)
MODEL_ID = "meta.llama3-8b-instruct-v1:0"
REGION = "us-east-1"

# 1. Setup Clients
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

def retrieve_from_kb(query):
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
    Step 2: Send the Question + Context + Language Instruction to Llama 3.
    """
    if not retrieved_docs:
        return "Sorry, I couldn't find any documents to answer that."

    # Prepare Context
    context_text = ""
    print("\n📄 FOUND CONTEXT:")
    for doc in retrieved_docs:
        text = doc['content']['text']
        uri = doc['location']['s3Location']['uri']
        print(f" - Found in: {uri}")
        context_text += f"{text}\n"

    # --- DYNAMIC PROMPT (Adds Language Instruction) ---
    system_instruction = f"""You are an expert on Saudi ZATCA regulations. 
    You must answer the user's question strictly based on the context provided below.
    
    IMPORTANT: You must answer in {language}.
    """

    formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_instruction}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Context:
{context_text}

Question: 
{query}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

    # --- PAYLOAD ---
    body = json.dumps({
        "prompt": formatted_prompt,
        "max_gen_len": 512,
        "temperature": 0.5,
        "top_p": 0.9
    })

    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=body
        )
        
        response_body = json.loads(response.get("body").read())
        return response_body['generation']

    except Exception as e:
        return f"❌ Generation Error: {str(e)}"

    # Prepare Context
    context_text = ""
    print("\n📄 FOUND CONTEXT:")
    for doc in retrieved_docs:
        text = doc['content']['text']
        uri = doc['location']['s3Location']['uri']
        print(f" - Found in: {uri}")
        context_text += f"{text}\n"

    # --- LLAMA 3 SPECIFIC PROMPT FORMAT ---
    # Llama 3 requires this specific tag structure to work well
    formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a helpful expert on Saudi ZATCA regulations. Answer using ONLY the context provided.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Context:
{context_text}

Question: 
{query}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

    # --- LLAMA 3 SPECIFIC PAYLOAD ---
    body = json.dumps({
        "prompt": formatted_prompt,
        "max_gen_len": 512,
        "temperature": 0.5,
        "top_p": 0.9
    })

    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=body
        )
        
        response_body = json.loads(response.get("body").read())
        # Llama 3 returns the answer in 'generation'
        return response_body['generation']

    except Exception as e:
        return f"❌ Generation Error: {str(e)}"

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    question = "What are the requirements for ZATCA integration?"
    
    docs = retrieve_from_kb(question)
    
    if docs:
        answer = generate_answer(question, docs)
        print("\n------------------------------------------------")
        print("🤖 VISIONQUEST ANSWER (Powered by Llama 3):")
        print(answer)
        print("------------------------------------------------")
    else:
        print("No info found.")
import boto3
import json

# 1. Setup the Bedrock Client
# We use 'bedrock-runtime' to invoke models.
# Make sure your AWS CLI is configured (aws configure) with credentials that have Bedrock access.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

def ask_claude(prompt):
    print(f"🤖 Sending prompt to Claude: '{prompt}'...")
    
    # 2. Prepare the Request
    # This is the specific format Claude 3 expects
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    # 3. Call the Model (The API Call)
    try:
        response = client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0", # Check your exact ID in the console if this fails
            body=body
        )
        
        # 4. Parse the Response
        response_body = json.loads(response.get("body").read())
        answer = response_body["content"][0]["text"]
        return answer

    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Test Question
    question = "Explain to me in one sentence why Data Sovereignty is important for Saudi Arabia."
    
    result = ask_claude(question)
    
    print("\n------------------------------------------------")
    print("📝 CLAUDE'S ANSWER:")
    print(result)
    print("------------------------------------------------")
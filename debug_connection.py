import requests
import json

# --- CONFIGURATION ---
# PASTE THE OUTPUT OF 'terraform output api_url' BELOW
# Ensure NO trailing slash (e.g., "https://xyz.amazonaws.com")
API_URL = "https://r79hipbsdc.execute-api.us-east-1.amazonaws.com".rstrip('/') 

print(f"🕵️ PROBING: {API_URL}")

# 1. Test Endpoint
url = f"{API_URL}/ingest"
print(f"📡 POST {url}")

# 2. Payload
payload = {
    "user_id": "debug_user", 
    "chat_id": "debug_chat",
    "file_name": "test.pdf",
    "file_content": "ZHVtbXk=", # "dummy" in base64
    "question": "Connection test"
}

try:
    response = requests.post(url, json=payload, timeout=10)
    
    print(f"\n⬇️ STATUS: {response.status_code}")
    print(f"📜 BODY:   {response.text}")

    if response.status_code == 200:
        print("\n✅ CONNECTION SUCCESSFUL!")
        print("The Backend is ALIVE. The issue is purely inside 'app.py' or 'secrets.toml' location.")
    elif response.status_code == 403:
        print("\n❌ 403 FORBIDDEN - API Gateway is blocking access (CORS or WAF).")
    elif response.status_code == 404:
        print("\n❌ 404 NOT FOUND - The URL is wrong.")
    else:
        print("\n❌ SERVER ERROR - Check CloudWatch Logs.")

except Exception as e:
    print(f"\n❌ CONNECT FAILED: {e}")
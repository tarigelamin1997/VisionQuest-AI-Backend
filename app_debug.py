import streamlit as st
import requests
import time
import base64
import json

# --- 1. CONFIGURATION (HARDCODED) ---
# We bypass secrets.toml entirely.
API_URL = "https://r79hipbsdc.execute-api.us-east-1.amazonaws.com"

st.set_page_config(page_title="VisionQuest Debugger", layout="centered")

# --- 2. INTERNAL API CLIENT (INLINED) ---
def debug_submit_job(file_bytes, file_name):
    url = f"{API_URL}/ingest"
    payload = {
        "user_id": "debug_user",
        "chat_id": "debug_session",
        "file_name": file_name,
        "file_content": base64.b64encode(file_bytes).decode('utf-8'),
        "question": "Summarize this document."
    }
    
    try:
        st.write(f"📤 Sending request to: `{url}`")
        response = requests.post(url, json=payload, timeout=20)
        
        if response.status_code == 200:
            return response.json().get('job_id')
        else:
            st.error(f"❌ API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ Connection Failed: {str(e)}")
        return None

def debug_check_status(job_id):
    url = f"{API_URL}/status"
    try:
        response = requests.post(url, json={'job_id': job_id}, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "ERROR"}
    except:
        return {"status": "ERROR"}

# --- 3. THE UI ---
st.title("🛠️ VisionQuest Connection Test")
st.write("This tool bypasses all config files to test the full pipeline.")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file:
    if st.button("🚀 Process File"):
        # A. Upload
        with st.status("1️⃣ Uploading to Cloud...", expanded=True) as status:
            file_bytes = uploaded_file.read()
            job_id = debug_submit_job(file_bytes, uploaded_file.name)
            
            if job_id:
                status.write(f"✅ Job Created! ID: `{job_id}`")
                status.update(label="2️⃣ AI Processing...", state="running")
                
                # B. Poll for Results
                progress_bar = st.progress(0)
                for i in range(30): # Wait up to 60 seconds
                    res = debug_check_status(job_id)
                    current_status = res.get("status")
                    
                    if current_status == "SUCCESS":
                        progress_bar.progress(100)
                        status.update(label="✅ Complete!", state="complete", expanded=False)
                        
                        st.divider()
                        st.success("🎉 IT WORKS!")
                        st.markdown(f"### 🤖 AI Response:\n{res.get('answer')}")
                        st.json(res) # Show full debug data
                        break
                    
                    elif current_status == "FAILED":
                        status.update(label="❌ Failed", state="error")
                        st.error("The backend reported a failure.")
                        break
                    
                    else:
                        # Still Processing
                        status.write(f"⏳ Backend Status: {current_status}...")
                        progress_bar.progress((i + 1) * 3)
                        time.sleep(2)
            else:
                status.update(label="❌ Upload Failed", state="error")
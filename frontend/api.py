import requests
import streamlit as st

def clean_url(base_url, endpoint):
    """Prevents double slashes in URL."""
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

def submit_job(base_url, payload):
    url = clean_url(base_url, "ingest")
    try:
        # 60s Timeout for large files/cold starts
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 413:
            st.error("❌ File too large. AWS Lambda limit is 6MB (approx 4MB PDF).")
            return None
            
        if response.status_code != 200:
            st.error(f"Server Error ({response.status_code}): {response.text}")
            return None
            
        return response.json().get('job_id')

    except Exception as e:
        st.error(f"Connection Failed: {str(e)}")
        return None

def check_status(base_url, job_id):
    url = clean_url(base_url, "status")
    try:
        response = requests.post(url, json={'job_id': job_id}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "ERROR", "error_msg": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "ERROR", "error_msg": str(e)}

def get_user_chats(base_url, user_id):
    """Fetches chat history."""
    url = clean_url(base_url, "history")
    try:
        response = requests.post(url, json={'user_id': user_id}, timeout=5)
        if response.status_code == 200:
            return response.json().get('chats', [])
        return []
    except:
        return []
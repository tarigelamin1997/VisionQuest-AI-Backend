import requests
import streamlit as st

def submit_job(api_url, payload, token=None):
    """Sends data to the Ingest Lambda"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token # Future proofing
        
    try:
        response = requests.post(f"{api_url}/submit", json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("job_id")
        else:
            st.error(f"⚠️ Server Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

def check_status(api_url, job_id):
    """Pings the Status Lambda"""
    try:
        response = requests.post(f"{api_url}/status", json={"job_id": job_id}, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "ERROR", "message": str(response.text)}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
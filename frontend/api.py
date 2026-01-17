import requests
import streamlit as st

def submit_job(api_url, payload, token=None):
    """Sends user data to /submit to start an async job"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    # Clean URL to avoid https://addr.com//submit
    url = f"{api_url.rstrip('/')}/submit"
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("job_id")
        else:
            st.error(f"Backend Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection Failed: {e}")
        return None

def check_status(api_url, job_id):
    """Pings /status to see if the AI is done thinking"""
    url = f"{api_url.rstrip('/')}/status"
    try:
        response = requests.post(url, json={"job_id": job_id}, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "ERROR"}
    except Exception:
        return {"status": "ERROR"}

def get_user_chats(api_url, user_id):
    """Fetches the list of all past chat titles for the sidebar"""
    url = f"{api_url.rstrip('/')}/history"
    params = {"action": "list_chats", "user_id": user_id}
    try:
        response = requests.get(url, params=params, timeout=5)
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []

def get_chat_history(api_url, chat_id):
    """Fetches every message/answer for a specific chat ID"""
    url = f"{api_url.rstrip('/')}/history"
    params = {"chat_id": chat_id}
    try:
        response = requests.get(url, params=params, timeout=5)
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []
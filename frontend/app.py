import streamlit as st
import time
import base64
import uuid
# from streamlit_mic_recorder import mic_recorder # Uncomment if you installed this
import requests

# --- MODULE IMPORTS ---
import auth
import api

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest SaaS", page_icon="💎", layout="wide")

# ==============================================================================
# 🚨 HARDCODED CONFIGURATION (The "Ease Our Life" Section)
# ==============================================================================
API_URL = "https://r79hipbsdc.execute-api.us-east-1.amazonaws.com"
COGNITO_CLIENT_ID = "5cqcsg20lv1i8nivk7im1am7q7"
AWS_REGION = "us-east-1"
# ==============================================================================

# --- SESSION STATE INITIALIZATION ---

# 🚧 DEV MODE: Auto-Login as Developer
if "user" not in st.session_state:
    st.session_state.user = {
        "email": "dev@visionquest.com", 
        "token": "mock_token"
    }

if "messages" not in st.session_state: st.session_state.messages = []
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = str(uuid.uuid4())
if "chat_list" not in st.session_state: st.session_state.chat_list = []

# ==============================================================================
# 1. AUTHENTICATION VIEW (Skipped if User Exists)
# ==============================================================================
if not st.session_state.user:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("VisionQuest ID")
        tab1, tab2 = st.tabs(["Log In", "Sign Up"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In"):
                tokens = auth.login_user(email, password, COGNITO_CLIENT_ID, AWS_REGION)
                if tokens:
                    st.session_state.user = {"email": email, "token": tokens['AccessToken']}
                    st.rerun()

# ==============================================================================
# 2. APPLICATION VIEW
# ==============================================================================
else:
    # --- SIDEBAR (HISTORY) ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['email']}**")
        
        # New Chat Button
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.current_chat_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.caption("📜 **History**")
        
        # --- SAFE HISTORY LOADER ---
        # We wrap this in try/except so the app doesn't crash if api.py is out of sync
        if not st.session_state.chat_list:
            try:
                if hasattr(api, 'get_user_chats'):
                    st.session_state.chat_list = api.get_user_chats(API_URL, st.session_state.user['email'])
                else:
                    st.warning("API update pending...")
            except Exception as e:
                print(f"History Error: {e}")

        # Display History Items
        for chat in st.session_state.chat_list:
            label = f"Chat {chat.get('chat_id', 'Unknown')[:8]}..."
            if st.button(label, key=chat.get('chat_id')):
                st.session_state.current_chat_id = chat['chat_id']
                
                # Fetch messages
                try:
                    # Note: We assume get_chat_history is implemented or we skip
                    if hasattr(api, 'get_chat_history'):
                        history = api.get_chat_history(API_URL, chat['chat_id'])
                        
                        reconstructed = []
                        for item in history:
                            # User Question
                            reconstructed.append({"role": "user", "content": item.get('user_prompt', '📝 Previous Query')})
                            
                            # AI Answer (CHECKING FOR 'SUCCESS' NOW)
                            if item.get('status') == 'SUCCESS':
                                reconstructed.append({
                                    "role": "assistant", 
                                    "content": item.get('answer'),
                                    "citations": item.get('citations')
                                })
                        st.session_state.messages = reconstructed
                        st.rerun()
                except:
                    pass

        st.divider()
        if st.button("Log Out"):
            st.session_state.user = None
            st.rerun()

    # --- MAIN CHAT AREA ---
    st.title("💎 VisionQuest AI")

    # Render Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("citations"):
                with st.expander("📚 Sources"):
                    st.json(msg["citations"])

    # --- INPUTS ---
    prompt = st.chat_input("Ask VisionQuest...")
    
    # File Uploader
    uploaded_file = st.file_uploader("Upload Document", type=['png', 'jpg', 'pdf'])
    
    payload = None
    display_msg = ""

    # 1. File + Text
    if uploaded_file and prompt:
        with st.spinner("Encoding file..."):
            bytes_data = uploaded_file.getvalue()
            b64_file = base64.b64encode(bytes_data).decode('utf-8')
            payload = {
                "file_content": b64_file, # Updated key name to match backend
                "file_name": uploaded_file.name, 
                "question": prompt,
                "user_id": st.session_state.user['email'],
                "chat_id": st.session_state.current_chat_id
            }
            display_msg = f"📄 *{uploaded_file.name}* - {prompt}"

    # 2. Text Only
    elif prompt:
        # For now, text-only might not work if backend expects a file, 
        # but let's keep the logic for future V2
        st.warning("Please upload a document to ask a question.")

    # --- SUBMIT & PROCESS ---
    if payload:
        # Add User Message to UI immediately
        st.session_state.messages.append({"role": "user", "content": display_msg})
        
        # Show Status Container
        with st.status("🚀 VisionQuest Activated...", expanded=True) as status:
            status.write("📤 Uploading to Cloud...")
            job_id = api.submit_job(API_URL, payload)
            
            if job_id:
                status.write(f"🎫 Job ID: `{job_id}`")
                status.write("🧠 AI Processing...")
                
                # Poll for Results
                progress = status.progress(0)
                for i in range(40): # Wait up to 80 seconds
                    res = api.check_status(API_URL, job_id)
                    current_status = res.get("status")
                    
                    if current_status == "SUCCESS":
                        progress.progress(100)
                        status.update(label="✅ Complete!", state="complete", expanded=False)
                        
                        # Add AI Response
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": res.get("answer"),
                            "citations": res.get("citations")
                        })
                        st.rerun()
                        break
                    
                    elif current_status == "FAILED":
                        status.update(label="❌ Failed", state="error")
                        st.error(f"Backend Error: {res.get('error_msg')}")
                        break
                    
                    # Still Processing
                    status.write(f"⏳ Status: {current_status}...")
                    time.sleep(2)
            else:
                status.update(label="❌ Connection Failed", state="error")
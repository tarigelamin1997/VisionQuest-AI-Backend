import streamlit as st
import time
import base64
from streamlit_mic_recorder import mic_recorder

# --- MODULE IMPORTS ---
import auth
import api

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest SaaS", page_icon="💎", layout="wide")

# --- CONFIGURATION ---
API_URL = st.secrets["api"]["url"]
COGNITO_CLIENT_ID = st.secrets["auth"]["client_id"]
AWS_REGION = st.secrets["auth"]["region"]

# --- SESSION STATE ---
if "user" not in st.session_state: st.session_state.user = None
if "messages" not in st.session_state: st.session_state.messages = []

# ==============================================================================
# 1. AUTHENTICATION VIEW
# ==============================================================================
if not st.session_state.user:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("VisionQuest ID")
        tab1, tab2, tab3 = st.tabs(["Log In", "Sign Up", "Verify"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In"):
                tokens = auth.login_user(email, password, COGNITO_CLIENT_ID, AWS_REGION)
                if tokens:
                    st.session_state.user = {"email": email, "token": tokens['AccessToken']}
                    st.rerun()

        with tab2:
            new_email = st.text_input("Email", key="new_email")
            new_pass = st.text_input("Password", type="password", key="new_pass")
            if st.button("Create Account"):
                auth.sign_up_user(new_email, new_pass, COGNITO_CLIENT_ID, AWS_REGION)

        with tab3:
            v_email = st.text_input("Email", key="v_email")
            v_code = st.text_input("Code", key="v_code")
            if st.button("Verify"):
                auth.verify_user(v_email, v_code, COGNITO_CLIENT_ID, AWS_REGION)

# ==============================================================================
# 2. APPLICATION VIEW
# ==============================================================================
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['email']}**")
        if st.button("Log Out"):
            st.session_state.user = None
            st.rerun()
        
        st.divider()
        st.caption("🎙️ Voice Input")
        voice_data = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", format="webm", key="mic")
        
        st.divider()
        uploaded_file = st.file_uploader("📂 Upload File", type=['png', 'jpg', 'pdf'])

    # --- MAIN CHAT ---
    st.title("💎 VisionQuest AI")

    # Render History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("citations"):
                with st.expander("📚 Sources"):
                    st.json(msg["citations"])

    # --- INPUT LOGIC ---
    prompt = st.chat_input("Ask VisionQuest...")
    payload = None
    display_msg = ""

    if voice_data and "voice_processed" not in st.session_state:
        st.session_state.voice_processed = True
        b64_audio = base64.b64encode(voice_data['bytes']).decode('utf-8')
        payload = {"audio": b64_audio, "user_id": st.session_state.user['email']}
        display_msg = "🎤 *Voice Message Submitted*"

    elif uploaded_file and prompt:
        bytes_data = uploaded_file.getvalue()
        b64_file = base64.b64encode(bytes_data).decode('utf-8')
        payload = {
            "file_data": b64_file, 
            "file_name": uploaded_file.name, 
            "question": prompt,
            "user_id": st.session_state.user['email']
        }
        display_msg = f"📄 *{uploaded_file.name}* - {prompt}"
        uploaded_file = None

    elif prompt:
        payload = {"question": prompt, "user_id": st.session_state.user['email']}
        display_msg = prompt

    # --- ASYNC EXECUTION ---
    if payload:
        st.session_state.messages.append({"role": "user", "content": display_msg})
        st.rerun() # Show user message immediately

    # Check if we need to process the last user message (Optimization)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_msg = st.session_state.messages[-1]["content"]
        # In a real app, you'd store the payload in state, not reconstruct it. 
        # For V1, assume payload exists if we just refreshed.
        if payload: 
            with st.status("🚀 Processing...", expanded=True) as status:
                job_id = api.submit_job(API_URL, payload)
                
                if job_id:
                    status.write("🧠 Thinking...")
                    progress = status.progress(0)
                    
                    for i in range(30):
                        res = api.check_status(API_URL, job_id)
                        if res.get("status") == "COMPLETED":
                            progress.progress(100)
                            status.update(label="Done!", state="complete", expanded=False)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": res.get("answer"),
                                "citations": res.get("citations")
                            })
                            st.rerun()
                            break
                        elif res.get("status") == "FAILED":
                            status.update(label="Failed", state="error")
                            st.error(res.get("error_msg"))
                            break
                        
                        progress.progress(min(90, (i + 1) * 5))
                        time.sleep(2)
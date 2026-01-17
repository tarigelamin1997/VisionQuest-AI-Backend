import streamlit as st
import time
import base64
import uuid
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

## ... (Imports and Config remain the same) ...

# --- SESSION STATE INITIALIZATION ---

# --------------------------------------------------------------------------
# 🚧 DEV MODE: BYPASS LOGIN
# --------------------------------------------------------------------------
# We initialize 'user' with fake credentials immediately.
# This tricks the app into thinking we are already logged in.
if "user" not in st.session_state:
    st.session_state.user = {
        "email": "dev@visionquest.com", 
        "token": "mock_token"
    }

# 🔒 PROD MODE: RESTORE THIS LATER
# if "user" not in st.session_state: st.session_state.user = None
# --------------------------------------------------------------------------

if "messages" not in st.session_state: st.session_state.messages = []
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = str(uuid.uuid4())
if "chat_list" not in st.session_state: st.session_state.chat_list = []

# ... (Rest of the file remains exactly the same) ...

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
        
        # Load History List (Once per session or on refresh)
        if not st.session_state.chat_list:
            st.session_state.chat_list = api.get_user_chats(API_URL, st.session_state.user['email'])

        # Display History Items
        for chat in st.session_state.chat_list:
            # Show chat ID (or title if we implemented titles)
            label = f"Chat {chat['chat_id'][:8]}..." 
            if st.button(label, key=chat['chat_id']):
                # Load the selected chat
                st.session_state.current_chat_id = chat['chat_id']
                # Fetch messages from backend
                history = api.get_chat_history(API_URL, chat['chat_id'])
                
                # Reconstruct message format for Streamlit
                reconstructed = []
                for item in history:
                    # User Question
                    if item.get('type') == 'text':
                         reconstructed.append({"role": "user", "content": "📝 (Text Input)"}) # Placeholder as we didn't save raw q
                    elif item.get('type') == 'audio':
                         reconstructed.append({"role": "user", "content": "🎤 (Audio Input)"})
                    
                    # AI Answer
                    if item.get('status') == 'COMPLETED':
                        reconstructed.append({
                            "role": "assistant", 
                            "content": item.get('answer'),
                            "citations": item.get('citations')
                        })
                
                st.session_state.messages = reconstructed
                st.rerun()

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
    voice_data = mic_recorder(start_prompt="🔴 Rec", stop_prompt="⏹️", key="mic")
    uploaded_file = st.file_uploader("Upload", type=['png', 'jpg', 'pdf'], label_visibility="collapsed")
    
    payload = None
    display_msg = ""

    # 1. Voice
    if voice_data and "voice_processed" not in st.session_state:
        st.session_state.voice_processed = True
        b64_audio = base64.b64encode(voice_data['bytes']).decode('utf-8')
        payload = {
            "audio": b64_audio, 
            "user_id": st.session_state.user['email'],
            "chat_id": st.session_state.current_chat_id # Attach Chat ID!
        }
        display_msg = "🎤 *Voice Message Submitted*"

    # 2. File + Text
    elif uploaded_file and prompt:
        bytes_data = uploaded_file.getvalue()
        b64_file = base64.b64encode(bytes_data).decode('utf-8')
        payload = {
            "file_data": b64_file, 
            "file_name": uploaded_file.name, 
            "question": prompt,
            "user_id": st.session_state.user['email'],
            "chat_id": st.session_state.current_chat_id
        }
        display_msg = f"📄 *{uploaded_file.name}* - {prompt}"

    # 3. Text Only
    elif prompt:
        payload = {
            "question": prompt, 
            "user_id": st.session_state.user['email'],
            "chat_id": st.session_state.current_chat_id
        }
        display_msg = prompt

    # --- SUBMIT & PROCESS ---
    if payload:
        st.session_state.messages.append({"role": "user", "content": display_msg})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        # Check if we just sent this (simple check to avoid reprocessing on reload)
        # In production, use a more robust state flag
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
                            # Refresh chat list to show this new interaction if it's new
                            st.session_state.chat_list = [] 
                            st.rerun()
                            break
                        elif res.get("status") == "FAILED":
                            status.update(label="Failed", state="error")
                            st.error(res.get("error_msg"))
                            break
                        
                        progress.progress(min(90, (i + 1) * 5))
                        time.sleep(2)
import streamlit as st
import requests
import json
import base64
import pandas as pd
from streamlit_mic_recorder import mic_recorder

# --- CONFIGURATION ---
ST_PAGE_TITLE = "VisionQuest AI"
try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "https://r79hipbsdc.execute-api.us-east-1.amazonaws.com/chat" 

# --- PAGE SETUP ---
st.set_page_config(
    page_title=ST_PAGE_TITLE,
    page_icon="👁️",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container {padding-top: 2rem;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stChatMessage {border-radius: 10px; border: 1px solid #ffffff20;}
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 VisionQuest")
    if st.button("🖊️ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    st.write("🎙️ **Voice**")
    # Note: We capture audio here. The processing happens in the main block.
    voice_input = mic_recorder(
        start_prompt="🔴 Record (Click to Start)",
        stop_prompt="⏹️ Stop (Click to Finish)",
        just_once=True,
        use_container_width=True,
        format="webm",
        key="recorder"
    )
    
    st.divider()

    st.write("📂 **Upload Data**")
    uploaded_file = st.file_uploader(
        "Upload Doc", 
        type=['jpg', 'jpeg', 'png', 'pdf', 'csv', 'xlsx'], 
        label_visibility="collapsed",
        key="file_uploader"
    )

# --- HELPER FUNCTIONS ---
def query_api(payload):
    try:
        # Increase timeout to 60 seconds to prevent "Black Screen" timeout
        response = requests.post(
            API_URL, 
            json=payload, 
            headers={"Content-Type": "application/json"},
            timeout=60 
        )
        if response.status_code == 200:
            return response.json()
        return {"answer": f"Error: {response.status_code} - {response.text}", "citations": []}
    except requests.exceptions.Timeout:
        return {"answer": "⚠️ Request timed out. The backend is taking too long.", "citations": []}
    except Exception as e:
        return {"answer": f"Connection Error: {e}", "citations": []}

def process_data_file(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        return f"DATA CONTEXT FROM USER FILE ({file.name}):\n\n" + df.to_markdown(index=False)
    except Exception as e:
        return f"Error reading data file: {e}"

# --- MAIN LOGIC ---

# 1. HANDLE VOICE (Top Priority)
if voice_input and voice_input['bytes']:
    
    # Only run if we haven't processed this specific audio yet (prevents loops)
    # We use a simple check: is the last message from user containing "🔊"?
    # If not, we process.
    
    with st.chat_message("user", avatar="👤"): 
        st.write("🔊 *Uploading & Transcribing (Please Wait...)*")
    
    # SHOW SPINNER TO PREVENT UI FREEZE
    with st.spinner("🎧 Transcribing Audio... (This takes ~10 seconds)"):
        b64_audio = base64.b64encode(voice_input['bytes']).decode('utf-8')
        data = query_api({"audio": b64_audio})
    
    # Display Result
    user_text = data.get('transcribed_text', '(No text detected)')
    answer = data.get('answer', 'No answer found.')
    citations = data.get('citations', [])

    st.session_state.messages.append({"role": "user", "content": f"🔊 {user_text}"})
    st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
    
    # Force rerun to show the chat bubble properly
    st.rerun()

# 2. HANDLE TEXT + FILES
if prompt := st.chat_input("Ask VisionQuest..."):
    
    payload = {"question": prompt}
    user_display = prompt
    
    if uploaded_file is not None:
        file_type = uploaded_file.type
        file_name = uploaded_file.name
        
        # CSV/Excel Handling
        if "csv" in file_type or "spreadsheet" in file_type or "excel" in file_type:
            uploaded_file.seek(0)
            data_text = process_data_file(uploaded_file)
            payload["question"] = f"{prompt}\n\n{data_text}"
            user_display = f"📊 *[Analysis]* {prompt}"
        
        # PDF/Image Handling
        else:
            uploaded_file.seek(0)
            bytes_data = uploaded_file.read()
            b64_data = base64.b64encode(bytes_data).decode('utf-8')
            
            payload["file_data"] = b64_data
            payload["media_type"] = file_type 
            if "pdf" in file_type: payload["media_type"] = "application/pdf"
            elif "png" in file_type: payload["media_type"] = "image/png"
            elif "jpeg" in file_type or "jpg" in file_type: payload["media_type"] = "image/jpeg"

            icon = "📄" if "pdf" in file_type else "🖼️"
            user_display = f"{icon} *[File: {file_name}]* {prompt}"
    
    # Display User
    with st.chat_message("user", avatar="👤"): st.markdown(user_display)
    st.session_state.messages.append({"role": "user", "content": user_display})

    # Display AI (With Spinner)
    with st.chat_message("assistant", avatar="🧙‍♂️"):
        with st.spinner("✨ Reasoning..."):
            data = query_api(payload)
            
            answer = data.get("answer", "No answer.")
            citations = []
            if data.get("citations"):
                for cit in data.get("citations"):
                    for ref in cit.get('retrievedReferences', []):
                        uri = ref.get('location', {}).get('s3Location', {}).get('uri', '')
                        name = uri.split('/')[-1]
                        citations.append(f"**{name}**")
            
            st.markdown(answer)
            if citations:
                with st.expander("📚 Sources"):
                    for c in citations: st.info(c)
        
        st.session_state.messages.append({"role": "assistant", "content": answer, "citations": data.get("citations")})
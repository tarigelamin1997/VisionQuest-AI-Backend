import streamlit as st
import boto3
import time
import json
import os
import pandas as pd
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
BUCKET_NAME = "visionquest-kb-tarig-001"
TABLE_NAME = "VisionQuest_Ingestion_Logs"
REGION = "us-east-1"

# --- CLIENTS ---
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest AI", page_icon="🤖", layout="wide")

# --- DEBUGGING: LOGO PATH ---
# If you don't see the logo, look at the path printed at the top of the sidebar
current_dir = os.getcwd()

# --- ASSETS LOADER ---
def load_text(lang_code):
    try:
        with open(f"assets/{lang_code}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {} # Fallback

# --- SESSION STATE (Memory) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your Vision 2030 Consultant. How can I help you with your compliance today?"}
    ]

# --- SIDEBAR (Settings & Upsell) ---
with st.sidebar:
    # 1. LOGO DEBUGGER
    if os.path.exists("logo.svg"):
        st.image("logo.svg", width=180)
    else:
        st.error(f"⚠️ Logo not found in: {current_dir}")

    # 2. LANGUAGE
    lang_choice = st.radio("Language / اللغة", ["English", "العربية"], horizontal=True)
    lang_code = "ar" if lang_choice == "العربية" else "en"
    txt = load_text(lang_code)
    
    st.markdown("---")
    
    # 3. THE UPSELL (The "Extra Candy") 🍬
    with st.expander("💎 **Compliance Inspector (Pro)**", expanded=False):
        st.info("Upload documents for AI Analysis & Translation.")
        uploaded_file = st.file_uploader("Upload File", type=['txt', 'pdf', 'png'])
        
        if uploaded_file and st.button("🚀 Analyze Now"):
            # Reuse your working S3/DynamoDB logic here
            try:
                with st.spinner("Sending to AI Factory..."):
                    uploaded_file.seek(0)
                    s3.put_object(Bucket=BUCKET_NAME, Key=f"raw/{uploaded_file.name}", Body=uploaded_file.read())
                st.success("Sent! Monitoring status...")
                
                # Simple Polling for the Upsell
                status_box = st.empty()
                for _ in range(10):
                    time.sleep(2)
                    # (Quick check logic would go here - simplified for UI focus)
                    status_box.info("🔄 AI is processing your file in the background...")
            except Exception as e:
                st.error(f"Error: {e}")

# --- MAIN CHAT INTERFACE ---
# Apply RTL if Arabic
if lang_code == "ar":
    st.markdown("""<style>.stChatMessage { direction: rtl; }</style>""", unsafe_allow_html=True)

st.title("🤖 VisionQuest Consultant")
st.caption("Ask about VAT, Regulations, or Vision 2030 Policies.")

# 1. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 2. Chat Input
if prompt := st.chat_input("Type your question here..."):
    # Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Add AI Response (Placeholder for RAG)
    with st.chat_message("assistant"):
        response = "I am currently in 'UI Demo Mode'. In the next step, you will connect me to your RAG Knowledge Base to answer this using real data!"
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
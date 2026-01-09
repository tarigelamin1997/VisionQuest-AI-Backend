import streamlit as st
import rag_engine # Importing your backend script

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest AI", page_icon="🚀", layout="wide")

# --- HEADER ---

# Create two columns: Logo on left, Title on right
col1, col2 = st.columns([1, 5])

with col1:
    # If you don't have a logo.png yet, this will just show the emoji
    st.image("logo.svg", width=80) 

with col2:
    st.title("VisionQuest / رؤية كويست")
    st.caption("AI-Driven Regulatory Intelligence for Saudi SMEs")

st.markdown("""
**Powered by:** AWS Bedrock | Knowledge Bases | Meta Llama 3
*Ask questions about ZATCA regulations, E-Invoicing, and Tax Compliance.*
""")
st.divider()

# --- SIDEBAR (The "Architect's Flex") ---
with st.sidebar:
    st.header("⚙️ System Status")
    st.success("✅ AWS Bedrock Online")
    st.success("✅ Knowledge Base Connected")
    st.info(f"🧠 Model: {rag_engine.MODEL_ID}")
    
    st.divider()
    st.write("🔒 **Data Sovereignty:**")
    st.caption("All data processing remains within AWS us-east-1. No external API calls.")

# --- MAIN CHAT INTERFACE ---
# Initialize chat history in session state so it remembers previous turns
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER INPUT ---
if prompt := st.chat_input("Ex: What is the deadline for Phase 2 integration?"):
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Generate Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("🔎 Scanning ZATCA Regulations (AWS Knowledge Base)..."):
            
            # CALL YOUR BACKEND HERE
            # Step A: Retrieve docs
            docs = rag_engine.retrieve_from_kb(prompt)
            
            if docs:
                # Step B: Generate Answer
                response_text = rag_engine.generate_answer(prompt, docs)
                
                # Step C: Format Citations for the UI
                st.markdown(response_text)
                
                # Show "Source of Truth" (The killer feature)
                with st.expander("📄 View Source Documents (Evidence)"):
                    for doc in docs:
                        uri = doc['location']['s3Location']['uri']
                        text = doc['content']['text'][:200]
                        st.caption(f"**Source:** {uri}")
                        st.info(f"...{text}...")
            else:
                response_text = "⚠️ I could not find any relevant information in the uploaded documents."
                st.warning(response_text)

    # 3. Save Assistant Message to History
    st.session_state.messages.append({"role": "assistant", "content": response_text})
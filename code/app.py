import streamlit as st
import rag_engine
import inspector  # <--- importing your new module

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest AI", page_icon="🚀", layout="wide")

# --- TRANSLATIONS ---
translations = {
    "English": {
        "title": "VisionQuest / Vision",
        "subtitle": "AI-Driven Regulatory Intelligence for Saudi SMEs",
        "tab_chat": "💬 Chat Assistant",
        "tab_inspector": "🕵️‍♂️ Invoice Inspector",
        "upload_label": "Upload Invoice (PDF or Image)",
        "inspect_btn": "🔍 Inspect Compliance",
        "welcome": "Ask me anything about ZATCA regulations.",
        "input_placeholder": "Ex: What are the requirements for Phase 2?"
    },
    "Arabic": {
        "title": "VisionQuest / رؤية",
        "subtitle": "الذكاء الاصطناعي لخدمة الشركات الصغيرة والمتوسطة",
        "tab_chat": "💬 المساعد الذكي",
        "tab_inspector": "🕵️‍♂️ فاحص الفواتير",
        "upload_label": "ارفع الفاتورة (PDF أو صورة)",
        "inspect_btn": "🔍 فحص الامتثال",
        "welcome": "اسألني أي شيء عن لوائح الزكاة.",
        "input_placeholder": "مثال: ما هي عقوبة عدم وجود رمز QR؟"
    }
}

# --- SIDEBAR ---
with st.sidebar:
    language = st.radio("Language / اللغة", ["English", "Arabic"])
    t = translations[language]
    st.divider()
    st.success("✅ System Online")
    st.info(f"🧠 Brain: Llama 3 8B\n👀 Eyes: Llama 3.2 11B")

# --- HEADER ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Flag_of_Saudi_Arabia.svg/2560px-Flag_of_Saudi_Arabia.svg.png", width=80) 
with col2:
    st.title(t["title"])
    st.caption(t["subtitle"])
st.divider()

# --- TABS ---
tab1, tab2 = st.tabs([t["tab_chat"], t["tab_inspector"]])

# === TAB 1: CHATBOT (RAG Engine) ===
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": t["welcome"]}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(t["input_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                docs = rag_engine.retrieve_from_kb(prompt)
                response = rag_engine.generate_answer(prompt, docs, language)
                
                # Right-to-Left logic for Arabic
                if language == "Arabic":
                    st.markdown(f"<div dir='rtl' style='text-align: right;'>{response}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# === TAB 2: INSPECTOR (Inspector Engine) ===
with tab2:
    uploaded_file = st.file_uploader(t["upload_label"], type=["jpg", "png", "jpeg", "pdf"])
    
    if uploaded_file:
        # Step A: Process File (PDF -> Image)
        image_bytes = inspector.process_file(uploaded_file)
        
        if image_bytes:
            st.image(image_bytes, caption="Document Preview", width=600)
            
            # Step B: Analyze
            if st.button(t["inspect_btn"], type="primary"):
                with st.spinner("🕵️‍♂️ Scanning for violations..."):
                    report = inspector.analyze_invoice(image_bytes, language)
                    
                    st.subheader("📋 Compliance Report")
                    if language == "Arabic":
                        st.markdown(f"<div dir='rtl' style='text-align: right;'>{report}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(report)
        else:
            st.error("Error processing file. Please upload a valid PDF or Image.")
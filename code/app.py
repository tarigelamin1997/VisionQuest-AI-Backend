import streamlit as st
import rag_engine

# --- PAGE CONFIG ---
st.set_page_config(page_title="VisionQuest AI", page_icon="🚀", layout="wide")

# --- TRANSLATION DICTIONARY ---
# This keeps the code clean. We just look up the text based on language.
translations = {
    "English": {
        "title": "VisionQuest / Vision",
        "subtitle": "AI-Driven Regulatory Intelligence for Saudi SMEs",
        "sidebar_title": "⚙️ System Status",
        "bedrock_status": "✅ AWS Bedrock Online",
        "kb_status": "✅ Knowledge Base Connected",
        "sovereignty": "🔒 **Data Sovereignty:**",
        "sovereignty_desc": "All data processing remains within AWS us-east-1.",
        "input_placeholder": "Ex: What is the deadline for Phase 2?",
        "spinner": "🔎 Scanning ZATCA Regulations...",
        "source_label": "📄 View Source Documents",
        "no_info": "⚠️ I could not find any relevant information in the documents.",
        "welcome": "Ask me anything about ZATCA, E-Invoicing, or Tax Compliance."
    },
    "Arabic": {
        "title": "VisionQuest / رؤية",
        "subtitle": "الذكاء الاصطناعي لخدمة الشركات الصغيرة والمتوسطة (ZATCA)",
        "sidebar_title": "⚙️ حالة النظام",
        "bedrock_status": "✅ AWS Bedrock متصل",
        "kb_status": "✅ قاعدة المعرفة متصلة",
        "sovereignty": "🔒 **سيادة البيانات:**",
        "sovereignty_desc": "تتم معالجة جميع البيانات داخل سحابة AWS الآمنة.",
        "input_placeholder": "مثال: ما هي متطلبات المرحلة الثانية؟",
        "spinner": "🔎 جاري البحث في لوائح الزكاة...",
        "source_label": "📄 عرض المصادر الرسمية",
        "no_info": "⚠️ عذراً، لم أجد معلومات ذات صلة في الوثائق المرفقة.",
        "welcome": "اسألني أي شيء عن لوائح الزكاة، الفوترة الإلكترونية، أو الامتثال الضريبي."
    }
}

# --- SIDEBAR & LANGUAGE TOGGLE ---
with st.sidebar:
    # The Language Switcher
    language = st.radio("Language / اللغة", ["English", "Arabic"], index=0)
    
    # Get the text for the selected language
    t = translations[language]

    st.divider()
    st.header(t["sidebar_title"])
    st.success(t["bedrock_status"])
    st.success(t["kb_status"])
    
    st.divider()
    st.write(t["sovereignty"])
    st.caption(t["sovereignty_desc"])

# --- MAIN HEADER ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Flag_of_Saudi_Arabia.svg/2560px-Flag_of_Saudi_Arabia.svg.png", width=80) 
with col2:
    st.title(t["title"])
    st.caption(t["subtitle"])

st.divider()

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": t["welcome"]}]

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input(t["input_placeholder"]):
    
    # 1. Show User Question
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Generate Answer
    with st.chat_message("assistant"):
        with st.spinner(t["spinner"]):
            
            # --- CALL BACKEND WITH LANGUAGE ---
            docs = rag_engine.retrieve_from_kb(prompt)
            
            if docs:
                # We pass the selected 'language' variable here!
                response_text = rag_engine.generate_answer(prompt, docs, language)
                
                # Check if Arabic to adjust text direction (Optional visual polish)
                if language == "Arabic":
                    st.markdown(f"<div dir='rtl' style='text-align: right;'>{response_text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(response_text)
                
                # Citations
                with st.expander(t["source_label"]):
                    for doc in docs:
                        uri = doc['location']['s3Location']['uri']
                        text = doc['content']['text'][:200]
                        st.caption(f"**Source:** {uri}")
                        st.info(f"...{text}...")
            else:
                st.warning(t["no_info"])
                response_text = t["no_info"]

    st.session_state.messages.append({"role": "assistant", "content": response_text})
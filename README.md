# 🚀 VisionQuest / رؤية كويست
**AI-Driven Regulatory Intelligence for Saudi SMEs**

![Saudi Vision 2030](https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Flag_of_Saudi_Arabia.svg/64px-Flag_of_Saudi_Arabia.svg.png)

VisionQuest is a GenAI-powered compliance assistant designed to help Saudi SMEs navigate complex ZATCA regulations. Built on **AWS Bedrock**, it uses a Retrieval-Augmented Generation (RAG) architecture to provide accurate, citation-backed answers while ensuring 100% data sovereignty within AWS.

## 🏗️ Architecture
* **Brain (LLM):** Meta Llama 3 (via AWS Bedrock)
* **Knowledge Base:** ZATCA Regulations (PDFs stored in S3)
* **Orchestration:** AWS Bedrock Agents & Knowledge Bases
* **Frontend:** Streamlit (Python)
* **Infrastructure:** AWS us-east-1 (Data never leaves the VPC)

## ✨ Key Features
* **✅ Hallucination-Free:** Answers are grounded strictly in uploaded ZATCA documents.
* **✅ Data Sovereignty:** Uses local AWS Bedrock inference; no data is sent to external APIs (like OpenAI).
* **✅ Evidence-Based:** Every answer includes citations and links to the source PDF pages.
* **✅ Saudi-First Design:** Bilingual-ready interface with Saudi Vision 2030 theming.

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone [https://github.com/tarigelamin1997/VisionQuest-AI-Backend.git](https://github.com/tarigelamin1997/VisionQuest-AI-Backend.git)
   cd VisionQuest-AI-Backend

2. **Install Dependencies**
    pip install -r requirements.txt

3. **Configure AWS Credentials Ensure your local environment has access to AWS Bedrock:**
    aws configure

4. **Run the Application**
    streamlit run app.py

🔒 Security Note
This project explicitly uses Meta Llama 3 on AWS Bedrock to ensure compliance with data residency requirements. No external public APIs are used for inference.

Built for the AWS Saudi Hackathon 2026 by Tarig Elamin.
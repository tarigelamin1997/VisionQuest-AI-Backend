import boto3
import fitz  # PyMuPDF
import io

# --- CONFIGURATION ---
VISION_MODEL_ID = "us.meta.llama3-2-11b-instruct-v1:0"
REGION = "us-east-1"

# Setup Client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

def process_file(uploaded_file):
    """
    Takes a Streamlit UploadedFile (PDF or Image).
    Returns: Bytes of the image (PNG) ready for the AI.
    """
    file_content = uploaded_file.getvalue()
    
    # 1. If it's a PDF, convert first page to Image
    if uploaded_file.type == "application/pdf":
        try:
            print("📄 Processing PDF...")
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            page = pdf_document.load_page(0)  # Get first page
            pix = page.get_pixmap()
            return pix.tobytes("png")
        except Exception as e:
            print(f"❌ PDF Error: {e}")
            return None
            
    # 2. If it's already an image, just return bytes
    return file_content

def analyze_invoice(image_bytes, language="English"):
    """
    Sends the image to Llama 3.2 Vision for auditing.
    """
    print("🕵️‍♂️ Sending to Vision Model...")
    
    prompt_text = f"""
    Role: You are a strict ZATCA Tax Auditor.
    Task: Check this invoice image for compliance violations.
    
    Checklist:
    1. Is there a QR Code? (Critical)
    2. Is the VAT Registration Number present?
    3. Is the Date and Invoice Number clear?
    4. Are the calculations (Total = Subtotal + VAT) correct?
    
    Output: Provide a bulleted report in {language}. Start with '✅ COMPLIANT' or '❌ VIOLATION'.
    """

    messages = [
        {
            "role": "user",
            "content": [
                {"image": {"format": "png", "source": {"bytes": image_bytes}}},
                {"text": prompt_text}
            ]
        }
    ]

    try:
        response = bedrock_runtime.converse(
            modelId=VISION_MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
        )
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        return f"❌ Vision API Error: {str(e)}"
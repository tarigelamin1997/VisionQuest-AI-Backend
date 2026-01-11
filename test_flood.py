import boto3
import time

# --- CONFIGURATION ---
BUCKET_NAME = "visionquest-kb-tarig-001" # <--- CONFIRM THIS
s3 = boto3.client('s3', region_name='us-east-1')

def create_and_upload(filename, content):
    """Creates a dummy file and uploads it to the Trigger Folder"""
    print(f"🚀 Uploading {filename}...")
    s3.put_object(Bucket=BUCKET_NAME, Key=f"raw/{filename}", Body=content.encode('utf-8'))

# --- THE PAYLOAD ---
files = [
    ("policy_en.txt", "The Value Added Tax (VAT) in Saudi Arabia is 15%. Compliance is mandatory."),
    ("invoice_ar.txt", "قيمة الضريبة المضافة هي 15% ويجب دفعها في نهاية الشهر."),
    ("hybrid_doc.txt", "The invoice date is 2023-01-01. المجموع الكلي هو 500 ريال.")
]

if __name__ == "__main__":
    print(f"🌊 STARTING FLOOD TEST to {BUCKET_NAME}/raw/ ...")
    
    for fname, text in files:
        create_and_upload(fname, text)
        time.sleep(1) # Slight pause to see them arrive sequentially
        
    print("\n✅ Flood Complete! The Cloud is now processing.")
    print("Go to AWS Console -> DynamoDB -> 'Explore Items' to watch the magic.")
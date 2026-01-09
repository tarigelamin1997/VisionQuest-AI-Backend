import boto3

# Connect to Bedrock in US-EAST-1
client = boto3.client('bedrock', region_name='us-east-1')

print("🔍 SCANNING FOR AVAILABLE MODELS...")
try:
    # List ALL models from ALL providers
    response = client.list_foundation_models()
    
    found_any = False
    for model in response['modelSummaries']:
        # We only care about TEXT models that are ACTIVE
        if model['outputModalities'] == ['TEXT'] and model['modelLifecycle']['status'] == 'ACTIVE':
            print(f"✅ FOUND: {model['modelName']}")
            print(f"   ID: {model['modelId']}")
            print(f"   Provider: {model['providerName']}")
            print("-" * 30)
            found_any = True

    if not found_any:
        print("❌ No active text models found. This is an account permission issue.")

except Exception as e:
    print(f"❌ Error scanning models: {str(e)}")
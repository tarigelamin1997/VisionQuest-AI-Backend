import boto3
from botocore.exceptions import ClientError
import streamlit as st

def get_cognito_client(region):
    return boto3.client('cognito-idp', region_name=region)

def login_user(username, password, client_id, region):
    """Authenticates user and returns tokens"""
    client = get_cognito_client(region)
    try:
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': username, 'PASSWORD': password}
        )
        return response['AuthenticationResult']
    except ClientError as e:
        st.error(f"❌ Login failed: {e.response['Error']['Message']}")
        return None

def sign_up_user(username, password, client_id, region):
    """Registers a new user"""
    client = get_cognito_client(region)
    try:
        client.sign_up(
            ClientId=client_id,
            Username=username,
            Password=password
        )
        st.success("✅ Account created! Please check your email for the code.")
        return True
    except ClientError as e:
        st.error(f"❌ Sign up failed: {e.response['Error']['Message']}")
        return False

def verify_user(username, code, client_id, region):
    """Confirms email with the code"""
    client = get_cognito_client(region)
    try:
        client.confirm_sign_up(
            ClientId=client_id,
            Username=username,
            ConfirmationCode=code
        )
        st.success("✅ Verified! You can now log in.")
        return True
    except ClientError as e:
        st.error(f"❌ Verification failed: {e.response['Error']['Message']}")
        return False
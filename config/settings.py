"""Configuration settings for the application"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_config(key: str, default: str = '') -> str:
    """Get config value from Streamlit secrets (Cloud) or environment variables (local)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


class Config:
    # API Configuration
    API_ENDPOINT = _get_config('API_ENDPOINT', 'https://api.recruitment.ppl.how/recruitment-demo-backend/api/auth/generate-login-links')
    API_KEY = _get_config('API_KEY', 'roc56HfZOB38N8tGOYiS1bN2pzEXFPiJ9ROtz1BqB9cOwnlZap9CZufKCqCXZa8RXfDl42rTA5TTeCW5R0cp4SvZp4SnioHw7QN2LJMT2fPuyj41lwL1niVj2swneFxY')
    API_TIMEOUT = 30

    # Email Configuration (AWS SES)
    AWS_SES_ACCESS_KEY = _get_config('AWS_SES_ACCESS_KEY', 'AKIA57VDLNVTSM65BU5O')
    AWS_SES_SECRET_KEY = _get_config('AWS_SES_SECRET_KEY', '')
    AWS_SES_REGION = _get_config('AWS_SES_REGION', 'ap-southeast-1')
    SENDER_EMAIL = _get_config('SENDER_EMAIL', 'noreply_gr@ppl.how')
    SENDER_NAME = _get_config('SENDER_NAME', 'Exam Portal')

    # Default Values
    DEFAULT_PROGRAM_ID = _get_config('DEFAULT_PROGRAM_ID', '')
    DEFAULT_ROUND_ID = _get_config('DEFAULT_ROUND_ID', '')
    DEFAULT_SESSION_TIME = _get_config('DEFAULT_SESSION_TIME', '730h')

    # Email Sending Configuration
    DELAY_BETWEEN_EMAILS = 0.01
    BATCH_SIZE = 50
    MAX_RETRIES = 3

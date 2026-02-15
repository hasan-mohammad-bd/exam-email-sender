"""Configuration settings for the application"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Configuration
    API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://localhost:3001/api/auth/generate-login-links')
    API_KEY = os.getenv('API_KEY', '')
    API_TIMEOUT = 30

    # Email Configuration (AWS SES)
    AWS_SES_ACCESS_KEY = os.getenv('AWS_SES_ACCESS_KEY', '')
    AWS_SES_SECRET_KEY = os.getenv('AWS_SES_SECRET_KEY', '')
    AWS_SES_REGION = os.getenv('AWS_SES_REGION', 'ap-south-1')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply_gr@ppl.how')
    SENDER_NAME = os.getenv('SENDER_NAME', 'Exam Portal')

    # Default Values
    DEFAULT_PROGRAM_ID = os.getenv('DEFAULT_PROGRAM_ID', '')
    DEFAULT_ROUND_ID = os.getenv('DEFAULT_ROUND_ID', '')
    DEFAULT_SESSION_TIME = os.getenv('DEFAULT_SESSION_TIME', '730h')

    # Email Sending Configuration
    DELAY_BETWEEN_EMAILS = 1
    BATCH_SIZE = 50
    MAX_RETRIES = 3

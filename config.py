import os

API_TOKEN = os.environ.get('API_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not API_TOKEN:
    raise ValueError("API_TOKEN is not set. Please ensure it's available in the environment variables.")
if not CHAT_ID:
    raise ValueError("CHAT_ID is not set. Please ensure it's available in the environment variables.")

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
USERNAME = os.getenv("USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL")
ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")

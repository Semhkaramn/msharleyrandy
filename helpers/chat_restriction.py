import os
from telegram import Update

ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")

def check_chat_restriction(update: Update) -> bool:
    if not ALLOWED_CHAT_ID:
        return True

    if not update.effective_chat:
        return True

    allowed_ids = [int(x.strip()) for x in ALLOWED_CHAT_ID.split(",") if x.strip()]
    return update.effective_chat.id in allowed_ids

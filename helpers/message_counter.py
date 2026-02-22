from telegram import Update
from telegram.ext import ContextTypes
from models.message_count import increment_message_count

async def handle_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    if update.effective_chat.type == "private":
        return

    increment_message_count(update.effective_chat.id, update.effective_user.id)

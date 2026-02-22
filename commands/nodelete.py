from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import find_chat, update_chat

async def nodelete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle private messages
    if update.effective_chat.type == "private":
        chat_id, is_valid, error = await check_private_admin(update, context)
        if not is_valid:
            await update.message.reply_text(error)
            return
    else:
        # Group message
        if not await is_admin(update):
            await update.message.reply_text(get_text("only_admin"))
            return
        chat_id = update.effective_chat.id

    chat = find_chat(chat_id)
    new_value = not chat.nodelete

    update_chat(chat_id, nodelete=new_value)

    if new_value:
        await update.message.reply_text(get_text("nodelete_on"))
    else:
        await update.message.reply_text(get_text("nodelete_off"))

from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import find_chat, update_chat

async def nodelete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    chat = find_chat(update.effective_chat.id)
    new_value = not chat.nodelete

    update_chat(update.effective_chat.id, nodelete=new_value)

    if new_value:
        await update.message.reply_text(get_text("nodelete_on"))
    else:
        await update.message.reply_text(get_text("nodelete_off"))

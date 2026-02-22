from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import update_chat

async def winnermessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Bir mesaji yanitlayarak kullanin.")
        return

    reply_msg = update.message.reply_to_message
    winner_message = {"text": reply_msg.text or reply_msg.caption or ""}

    update_chat(update.effective_chat.id, winner_message=winner_message)
    await update.message.reply_text(get_text("winner_message_set"))

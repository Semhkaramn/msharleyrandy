from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import update_chat

async def number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle private messages
    if update.effective_chat.type == "private":
        chat_id, is_valid, error = await check_private_admin(update, context)
        if not is_valid:
            await update.message.reply_text(error)
            return
        args = list(context.args) if context.args else []
    else:
        # Group message
        if not await is_admin(update):
            await update.message.reply_text(get_text("only_admin"))
            return
        chat_id = update.effective_chat.id
        args = list(context.args) if context.args else []

    if not args or not args[0].isdigit():
        await update.message.reply_text("Kullanim: /number [sayi]")
        return

    number = int(args[0])
    if number < 1:
        number = 1

    update_chat(chat_id, number=number)
    await update.message.reply_text(get_text("number_set", number=number))

from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import update_chat

async def number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Kullanim: /number [sayi]")
        return

    number = int(context.args[0])
    if number < 1:
        number = 1

    update_chat(update.effective_chat.id, number=number)
    await update.message.reply_text(get_text("number_set", number=number))

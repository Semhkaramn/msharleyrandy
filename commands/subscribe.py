from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import update_chat

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    if not context.args:
        await update.message.reply_text("Kullanim: /subscribe @kanal_adi")
        return

    channel = context.args[0]
    if not channel.startswith("@"):
        channel = "@" + channel

    update_chat(update.effective_chat.id, subscribe=channel)
    await update.message.reply_text(get_text("subscribe_set", channel=channel))

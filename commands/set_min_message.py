from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import update_chat
from models.message_count import get_period_name_tr

async def setminmessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if not args:
        await update.message.reply_text("Kullanim: /setminmessage [sayi] [donem]\nDonem: daily, weekly, monthly, all\nOrnek: /setminmessage 10 daily")
        return

    try:
        count = int(args[0])
    except ValueError:
        await update.message.reply_text("Gecersiz sayi!")
        return

    period = "daily"
    if len(args) > 1:
        period = args[1].lower()
        if period not in ["daily", "weekly", "monthly", "all"]:
            period = "daily"

    if count <= 0:
        update_chat(chat_id, min_message_count=0)
        await update.message.reply_text(get_text("min_message_removed"))
    else:
        update_chat(chat_id, min_message_count=count, message_period=period)
        period_name = get_period_name_tr(period)
        await update.message.reply_text(get_text("min_message_set", count=count, period=period_name))

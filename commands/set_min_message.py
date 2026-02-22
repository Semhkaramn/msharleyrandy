from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import update_chat
from models.message_count import get_period_name_tr

async def setminmessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    if not context.args:
        await update.message.reply_text("Kullanim: /setminmessage [sayi] [donem]\nDonem: daily, weekly, monthly, all\nOrnek: /setminmessage 10 daily")
        return

    try:
        count = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Gecersiz sayi!")
        return

    period = "daily"
    if len(context.args) > 1:
        period = context.args[1].lower()
        if period not in ["daily", "weekly", "monthly", "all"]:
            period = "daily"

    if count <= 0:
        update_chat(update.effective_chat.id, min_message_count=0)
        await update.message.reply_text(get_text("min_message_removed"))
    else:
        update_chat(update.effective_chat.id, min_message_count=count, message_period=period)
        period_name = get_period_name_tr(period)
        await update.message.reply_text(get_text("min_message_set", count=count, period=period_name))

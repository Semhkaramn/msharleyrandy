from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import find_chat
from models.message_count import get_period_name_tr

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    chat = find_chat(update.effective_chat.id)

    subscribe_text = chat.subscribe if chat.subscribe else "Yok"
    nodelete_text = "Kapali" if chat.nodelete else "Acik"
    period_name = get_period_name_tr(chat.message_period)

    await update.message.reply_text(get_text(
        "stats",
        number=chat.number,
        subscribe=subscribe_text,
        nodelete=nodelete_text,
        min_message=chat.min_message_count,
        period=period_name
    ))

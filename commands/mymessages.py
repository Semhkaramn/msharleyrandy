from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from models.chat import find_chat
from models.message_count import get_user_message_count_by_period, get_period_name_tr

async def mymessages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    chat = find_chat(update.effective_chat.id)
    user_id = update.effective_user.id

    count = get_user_message_count_by_period(update.effective_chat.id, user_id, chat.message_period)
    period_name = get_period_name_tr(chat.message_period)

    await update.message.reply_text(get_text("your_messages", period=period_name, count=count))

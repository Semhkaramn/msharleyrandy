from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import find_chat
from models.message_count import get_period_name_tr

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    subscribe_text = chat.subscribe if chat.subscribe else "Yok"
    nodelete_text = "Kapali" if chat.nodelete else "Acik"
    period_name = get_period_name_tr(chat.message_period)

    stats_text = get_text(
        "stats",
        number=chat.number,
        subscribe=subscribe_text,
        nodelete=nodelete_text,
        min_message=chat.min_message_count,
        period=period_name
    )

    # Add chat_id info for private messages
    if update.effective_chat.type == "private":
        stats_text += f"\n\nChat ID: {chat_id}"

    await update.message.reply_text(stats_text)

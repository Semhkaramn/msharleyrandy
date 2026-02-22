import os
import logging
from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from models.database import init_db
from helpers.chat_restriction import check_chat_restriction
from helpers.locale import get_text
from helpers.message_counter import handle_message_count

from commands.start_help import start_command, help_command
from commands.randy import randy_command, participate_callback, finish_raffle
from commands.number import number_command
from commands.subscribe import subscribe_command
from commands.nosubscribe import nosubscribe_command
from commands.raffle_message import rafflemessage_command
from commands.winner_message import winnermessage_command
from commands.nodelete import nodelete_command
from commands.set_min_message import setminmessage_command
from commands.stats import stats_command
from commands.mymessages import mymessages_command

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

async def restriction_middleware(update: Update, context):
    if not check_chat_restriction(update):
        if update.message:
            await update.message.reply_text(get_text("not_allowed"))
        return False
    return True

async def message_handler(update: Update, context):
    if not await restriction_middleware(update, context):
        return
    await handle_message_count(update, context)

async def forward_handler(update: Update, context):
    if not update.message or not update.message.forward_from_chat:
        return

    if update.effective_chat.type != "private":
        return

    from models.raffle import get_raffle_by_message
    from models.chat import find_chat

    forward_chat_id = update.message.forward_from_chat.id
    forward_message_id = update.message.forward_from_message_id

    raffle = get_raffle_by_message(forward_chat_id, forward_message_id)
    if not raffle:
        return

    try:
        chat = find_chat(forward_chat_id)
        result = await finish_raffle(raffle.id, context, forward_chat_id)
        if result:
            await context.bot.send_message(
                forward_chat_id,
                result,
                parse_mode="HTML"
            )
            await update.message.reply_text("Cekilis tamamlandi!")
    except Exception as e:
        logger.error(f"Raffle finish error: {e}")
        await update.message.reply_text("Bir hata olustu, tekrar deneyin.")

def main():
    init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("randy", randy_command))
    app.add_handler(CommandHandler("number", number_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("nosubscribe", nosubscribe_command))
    app.add_handler(CommandHandler("rafflemessage", rafflemessage_command))
    app.add_handler(CommandHandler("winnermessage", winnermessage_command))
    app.add_handler(CommandHandler("nodelete", nodelete_command))
    app.add_handler(CommandHandler("setminmessage", setminmessage_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("mymessages", mymessages_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(participate_callback, pattern="^join_"))

    # Message handlers
    app.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, forward_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

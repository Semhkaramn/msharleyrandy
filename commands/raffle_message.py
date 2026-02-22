from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import update_chat

async def rafflemessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle private messages
    if update.effective_chat.type == "private":
        chat_id, is_valid, error = await check_private_admin(update, context)
        if not is_valid:
            await update.message.reply_text(error)
            return

        # In private, use text after command
        if not context.args:
            await update.message.reply_text("Kullanim: /rafflemessage [mesaj metni]")
            return

        text = " ".join(context.args)
        raffle_message = {"text": text}
        update_chat(chat_id, raffle_message=raffle_message)
        await update.message.reply_text(get_text("raffle_message_set"))
    else:
        # Group message - use reply
        if not await is_admin(update):
            await update.message.reply_text(get_text("only_admin"))
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("Bir mesaji yanitlayarak kullanin.")
            return

        reply_msg = update.message.reply_to_message
        raffle_message = {"text": reply_msg.text or reply_msg.caption or ""}

        update_chat(update.effective_chat.id, raffle_message=raffle_message)
        await update.message.reply_text(get_text("raffle_message_set"))

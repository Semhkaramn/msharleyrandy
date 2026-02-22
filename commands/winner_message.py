from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text
from helpers.check_admin import is_admin, check_private_admin
from models.chat import update_chat

async def winnermessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle private messages
    if update.effective_chat.type == "private":
        chat_id, is_valid, error = await check_private_admin(update, context)
        if not is_valid:
            await update.message.reply_text(error)
            return

        # In private, use text after command
        if not context.args:
            await update.message.reply_text(
                "Kullanim: /winnermessage [mesaj metni]\n\n"
                "Veya bir mesaji yanitlayarak kullanin.\n\n"
                "Ipucu:\n"
                "• $winner - Kazanan(lar)in adini gosterir\n"
                "• $numberOfParticipants - Toplam katilimci sayisini gosterir"
            )
            return

        text = " ".join(context.args)
        winner_message = {"text": text}
        update_chat(chat_id, winner_message=winner_message)
        await update.message.reply_text(get_text("winner_message_set"))
    else:
        # Group message - use reply
        if not await is_admin(update):
            await update.message.reply_text(get_text("only_admin"))
            return

        if not update.message.reply_to_message:
            await update.message.reply_text(
                "Bir mesaji yanitlayarak kullanin.\n\n"
                "Ipucu:\n"
                "• $winner - Kazanan(lar)in adini gosterir\n"
                "• $numberOfParticipants - Toplam katilimci sayisini gosterir"
            )
            return

        reply_msg = update.message.reply_to_message
        winner_message = {"text": reply_msg.text or reply_msg.caption or ""}

        update_chat(update.effective_chat.id, winner_message=winner_message)
        await update.message.reply_text(get_text("winner_message_set"))


async def nowinnermessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove custom winner message"""
    if update.effective_chat.type == "private":
        chat_id, is_valid, error = await check_private_admin(update, context)
        if not is_valid:
            await update.message.reply_text(error)
            return
    else:
        if not await is_admin(update):
            await update.message.reply_text(get_text("only_admin"))
            return
        chat_id = update.effective_chat.id

    update_chat(chat_id, winner_message=None)
    await update.message.reply_text("Ozel kazanan mesaji kaldirildi. Varsayilan mesaj kullanilacak.")

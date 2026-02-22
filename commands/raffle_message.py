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
            await update.message.reply_text(
                "Kullanim: /rafflemessage [mesaj metni]\n\n"
                "Veya bir mesaji (foto dahil) yanitlayarak kullanin.\n\n"
                "Ipucu: Mesajiniza $numberOfParticipants yazarsaniz, "
                "katilimci sayisi otomatik gosterilir."
            )
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
            await update.message.reply_text(
                "Bir mesaji yanitlayarak kullanin.\n\n"
                "Ipucu: Mesajiniza $numberOfParticipants yazarsaniz, "
                "katilimci sayisi otomatik gosterilir."
            )
            return

        reply_msg = update.message.reply_to_message

        # Build raffle message object with photo support
        raffle_message = {}

        # Check for photo
        if reply_msg.photo:
            # Get the largest photo
            photo = reply_msg.photo[-1]
            raffle_message["photo_id"] = photo.file_id
            raffle_message["caption"] = reply_msg.caption or ""
        elif reply_msg.animation:
            raffle_message["animation_id"] = reply_msg.animation.file_id
            raffle_message["caption"] = reply_msg.caption or ""
        elif reply_msg.video:
            raffle_message["video_id"] = reply_msg.video.file_id
            raffle_message["caption"] = reply_msg.caption or ""
        else:
            raffle_message["text"] = reply_msg.text or ""

        update_chat(update.effective_chat.id, raffle_message=raffle_message)
        await update.message.reply_text(get_text("raffle_message_set"))


async def norafflemessage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove custom raffle message"""
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

    update_chat(chat_id, raffle_message=None)
    await update.message.reply_text("Ozel cekilis mesaji kaldirildi. Varsayilan mesaj kullanilacak.")

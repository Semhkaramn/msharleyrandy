import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus, ParseMode
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import find_chat
from models.raffle import add_raffle, add_participant, update_raffle, get_raffle
from models.message_count import get_user_message_count_by_period, get_period_name_tr
from models.database import SessionLocal


def get_raffle_keyboard(raffle_id: int) -> InlineKeyboardMarkup:
    """Generate raffle participation button"""
    keyboard = [[InlineKeyboardButton(get_text("participate"), callback_data=f"join_{raffle_id}")]]
    return InlineKeyboardMarkup(keyboard)


def replace_participant_count(text: str, count: int) -> str:
    """Replace $numberOfParticipants placeholder with actual count"""
    if text:
        return text.replace("$numberOfParticipants", str(count))
    return text


async def randy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    chat = find_chat(update.effective_chat.id)
    raffle = add_raffle(update.effective_chat.id)

    reply_markup = get_raffle_keyboard(raffle.id)

    # Store raffle message and winner message from chat settings
    raffle_data = {}
    if chat.raffle_message:
        raffle_data["raffle_message"] = chat.raffle_message
    if chat.winner_message:
        raffle_data["winner_message"] = chat.winner_message
    if raffle_data:
        update_raffle(raffle.id, **raffle_data)

    # Send raffle message
    if chat.raffle_message:
        rm = chat.raffle_message

        if rm.get("photo_id"):
            # Send photo with caption
            caption = replace_participant_count(rm.get("caption", ""), 0)
            msg = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=rm["photo_id"],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        elif rm.get("animation_id"):
            # Send GIF
            caption = replace_participant_count(rm.get("caption", ""), 0)
            msg = await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=rm["animation_id"],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        elif rm.get("video_id"):
            # Send video
            caption = replace_participant_count(rm.get("caption", ""), 0)
            msg = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=rm["video_id"],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            # Send text
            text = replace_participant_count(rm.get("text", get_text("raffle_started")), 0)
            msg = await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    else:
        # Default raffle message
        raffle_text = get_text("raffle_started")
        msg = await update.message.reply_text(raffle_text, reply_markup=reply_markup)

    update_raffle(raffle.id, message_id=msg.message_id)

    # Try to delete the command message
    try:
        await update.message.delete()
    except:
        pass


async def participate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("join_"):
        return

    raffle_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    chat = find_chat(chat_id)

    # Abonelik kontrolu
    if chat.subscribe:
        channels = chat.subscribe.split(",")
        for channel in channels:
            channel = channel.strip()
            try:
                channel_id = channel if channel.startswith("-") or channel.isdigit() else f"@{channel}"
                member = await context.bot.get_chat_member(channel_id, user_id)
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    await query.answer(get_text("not_subscribed", channel=channel), show_alert=True)
                    return
            except Exception:
                await query.answer(get_text("not_subscribed", channel=channel), show_alert=True)
                return

    # Mesaj sarti kontrolu
    if chat.min_message_count > 0:
        user_count = get_user_message_count_by_period(chat_id, user_id, chat.message_period)
        if user_count < chat.min_message_count:
            period_name = get_period_name_tr(chat.message_period)
            await query.answer(
                get_text("min_message_required", period=period_name, count=chat.min_message_count, current=user_count),
                show_alert=True
            )
            return

    # Katilim
    db = SessionLocal()
    try:
        from models.raffle import Raffle
        raffle = db.query(Raffle).filter(Raffle.id == raffle_id).first()
        if not raffle:
            await query.answer(get_text("raffle_not_found"), show_alert=True)
            return

        if raffle.winners:
            await query.answer(get_text("raffle_ended"), show_alert=True)
            return

        if user_id in raffle.participants_ids:
            await query.answer(get_text("already_participated"), show_alert=True)
            return

        new_list = list(raffle.participants_ids) + [user_id]
        raffle.participants_ids = new_list
        db.commit()

        participant_count = len(new_list)
        await query.answer(get_text("participated"), show_alert=True)

        # Update message with new participant count
        reply_markup = get_raffle_keyboard(raffle.id)

        rm = raffle.raffle_message or chat.raffle_message

        if rm:
            if rm.get("photo_id") or rm.get("animation_id") or rm.get("video_id"):
                # Update caption for media messages
                caption = replace_participant_count(rm.get("caption", ""), participant_count)
                try:
                    await context.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=raffle.message_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
            else:
                # Update text message
                text = replace_participant_count(rm.get("text", ""), participant_count)
                if not text:
                    text = f"{get_text('raffle_started')}\n\n{get_text('participants')}: {participant_count}"
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=raffle.message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except:
                    pass
        else:
            # Default message with participant count
            text = f"{get_text('raffle_started')}\n\n{get_text('participants')}: {participant_count}"
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=raffle.message_id,
                    text=text,
                    reply_markup=reply_markup
                )
            except:
                pass
    finally:
        db.close()


async def finish_raffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish raffle by replying to the raffle message"""
    if not update.message.reply_to_message:
        return

    if not await is_admin(update):
        return

    chat_id = update.effective_chat.id
    message_id = update.message.reply_to_message.message_id

    result = await finish_raffle_by_message(message_id, context, chat_id)
    if result:
        # Try to delete the command
        try:
            await update.message.delete()
        except:
            pass


async def finish_raffle_by_message(message_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Finish raffle by message ID"""
    from models.raffle import get_raffle_by_message

    chat = find_chat(chat_id)
    raffle = get_raffle_by_message(chat_id, message_id)

    if not raffle:
        return None

    if raffle.winners:
        return None  # Already finished

    db = SessionLocal()
    try:
        from models.raffle import Raffle
        raffle = db.query(Raffle).filter(Raffle.id == raffle.id).first()
        if not raffle:
            return None

        participants = raffle.participants_ids
        participant_count = len(participants)

        if not participants:
            # No participants
            text = get_text("no_participants")
            if chat.nodelete:
                await context.bot.send_message(chat_id, text)
            else:
                try:
                    if raffle.raffle_message and (raffle.raffle_message.get("photo_id") or raffle.raffle_message.get("animation_id") or raffle.raffle_message.get("video_id")):
                        await context.bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=raffle.message_id,
                            caption=text,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=raffle.message_id,
                            text=text,
                            parse_mode=ParseMode.HTML
                        )
                except:
                    await context.bot.send_message(chat_id, text)
            raffle.winners = "none"
            db.commit()
            return text

        winner_count = min(chat.number, len(participants))
        winners = random.sample(participants, winner_count)

        winner_mentions = []
        winner_names = []
        for w_id in winners:
            try:
                user = await context.bot.get_chat_member(chat_id, w_id)
                name = user.user.first_name or "Kullanici"
                if user.user.username:
                    name = f"@{user.user.username}"
                winner_mentions.append(f"<a href='tg://user?id={w_id}'>{name}</a>")
                winner_names.append(name)
            except:
                winner_mentions.append(f"<a href='tg://user?id={w_id}'>Kullanici</a>")
                winner_names.append("Kullanici")

        raffle.winners = ",".join(map(str, winners))
        db.commit()

        # Build winner text
        wm = raffle.winner_message or chat.winner_message
        if wm and wm.get("text"):
            winner_text = wm["text"]
            winner_text = winner_text.replace("$winner", ", ".join(winner_mentions))
            winner_text = winner_text.replace("$numberOfParticipants", str(participant_count))
        else:
            if len(winners) == 1:
                winner_text = f"🎉 {get_text('winner')}: {winner_mentions[0]}!\n\n{get_text('congratulations')}!\n\n{get_text('participants')}: {participant_count}"
            else:
                winner_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(winner_mentions)])
                winner_text = f"🎉 {get_text('winners')}:\n{winner_list}\n\n{get_text('congratulations')}!\n\n{get_text('participants')}: {participant_count}"

        # Send or edit message
        if chat.nodelete:
            await context.bot.send_message(chat_id, winner_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            try:
                if raffle.raffle_message and (raffle.raffle_message.get("photo_id") or raffle.raffle_message.get("animation_id") or raffle.raffle_message.get("video_id")):
                    await context.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=raffle.message_id,
                        caption=winner_text,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=raffle.message_id,
                        text=winner_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
            except:
                await context.bot.send_message(chat_id, winner_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        return winner_text
    finally:
        db.close()


async def finish_raffle(raffle_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Legacy function - finish raffle by ID"""
    chat = find_chat(chat_id)

    db = SessionLocal()
    try:
        from models.raffle import Raffle
        raffle = db.query(Raffle).filter(Raffle.id == raffle_id).first()
        if not raffle:
            return None

        participants = raffle.participants_ids
        if not participants:
            return get_text("no_participants")

        winner_count = min(chat.number, len(participants))
        winners = random.sample(participants, winner_count)

        winner_mentions = []
        for w_id in winners:
            try:
                user = await context.bot.get_chat_member(chat_id, w_id)
                name = user.user.first_name or "Kullanici"
                winner_mentions.append(f"<a href='tg://user?id={w_id}'>{name}</a>")
            except:
                winner_mentions.append(f"<a href='tg://user?id={w_id}'>Kullanici</a>")

        raffle.winners = ", ".join(winner_mentions)
        db.commit()

        winner_text = get_text("winners") + "\n" + "\n".join(winner_mentions)
        if chat.winner_message:
            winner_text = chat.winner_message.get("text", winner_text)

        return winner_text
    finally:
        db.close()

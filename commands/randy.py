import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from helpers.locale import get_text
from helpers.check_admin import is_admin
from models.chat import find_chat
from models.raffle import add_raffle, add_participant, update_raffle, get_raffle
from models.message_count import get_user_message_count_by_period, get_period_name_tr
from models.database import SessionLocal

async def randy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        await update.message.reply_text(get_text("only_group"))
        return

    if not await is_admin(update):
        await update.message.reply_text(get_text("only_admin"))
        return

    chat = find_chat(update.effective_chat.id)
    raffle = add_raffle(update.effective_chat.id)

    keyboard = [[InlineKeyboardButton(get_text("participate"), callback_data=f"join_{raffle.id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    raffle_text = get_text("raffle_started")
    if chat.raffle_message:
        raffle_text = chat.raffle_message.get("text", raffle_text)

    msg = await update.message.reply_text(raffle_text, reply_markup=reply_markup)
    update_raffle(raffle.id, message_id=msg.message_id)

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
        try:
            member = await context.bot.get_chat_member(chat.subscribe, user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await query.answer(get_text("not_subscribed", channel=chat.subscribe), show_alert=True)
                return
        except Exception:
            await query.answer(get_text("not_subscribed", channel=chat.subscribe), show_alert=True)
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
        if raffle:
            if user_id in raffle.participants_ids:
                await query.answer(get_text("already_participated"), show_alert=True)
                return

            new_list = list(raffle.participants_ids) + [user_id]
            raffle.participants_ids = new_list
            db.commit()
            await query.answer(get_text("participated"), show_alert=True)
    finally:
        db.close()

async def finish_raffle(raffle_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
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

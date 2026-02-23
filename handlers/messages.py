"""
📨 Mesaj Handler
Grup mesajlarını işler - Roll sistemi ve mesaj sayma
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import IGNORED_USER_IDS
from templates import ROLL, format_roll_list
from services.message_service import track_message
from services.roll_service import (
    get_roll_state, start_roll, save_step, stop_roll,
    start_break, resume_roll, lock_roll, unlock_roll,
    track_user_message, get_status_list, clean_inactive_users
)
from services.randy_service import track_post_randy_message
from utils.admin_check import is_group_admin, is_system_user, can_anonymous_admin_use_commands


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Grup mesajlarını işler:
    1. Roll komutları (admin)
    2. Liste komutu (admin)
    3. Mesaj sayma
    4. Roll kullanıcı takibi
    5. Randy sonrası mesaj takibi
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not message or not message.text:
        return

    text = message.text.strip()
    lower_text = text.lower()

    # ========== SİSTEM HESABI KONTROLÜ ==========

    # Telegram servis hesabı (777000) - bağlı kanal mesajları
    if user and user.id in IGNORED_USER_IDS:
        return

    # Anonim admin kontrolü (GroupAnonymousBot - 1087968824)
    is_anonymous = message.sender_chat is not None and user and user.id == 1087968824

    # ========== ROLL KOMUTLARI (Admin) ==========

    # "liste" komutu
    if lower_text == 'liste':
        if is_anonymous:
            is_admin = can_anonymous_admin_use_commands(message)
        else:
            is_admin = await is_group_admin(context.bot, chat.id, user.id) if user else False

        if is_admin:
            status_msg = await get_status_list(chat.id)
            await message.reply_text(status_msg, parse_mode="HTML")
        return

    # Roll komutları
    if lower_text.startswith('roll ') or lower_text == 'roll':
        await handle_roll_command(update, context, lower_text)
        return

    # ========== MESAJ SAYMA VE ROLL TAKİBİ ==========

    # Sistem hesapları için mesaj sayma yapılmaz
    if not user or is_system_user(user.id) or is_anonymous:
        return

    # Paralel işlemler
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    # 1. Mesaj sayma
    await track_message(
        user_id, chat.id,
        username, first_name, last_name
    )

    # 2. Roll kullanıcı takibi
    roll_state = await get_roll_state(chat.id)

    if roll_state['status'] in ['active', 'locked', 'locked_break']:
        # Bot ve admin kontrolü - bunlar roll listesine eklenmez
        is_bot = user.is_bot if hasattr(user, 'is_bot') else False

        if not is_bot:
            is_admin = await is_group_admin(context.bot, chat.id, user_id)

            if not is_admin:
                await track_user_message(
                    chat.id, user_id,
                    username, first_name
                )

    # 3. Randy sonrası mesaj takibi
    await track_post_randy_message(
        chat.id, user_id,
        username, first_name
    )


async def handle_roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lower_text: str):
    """Roll komutlarını işler"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not message:
        return

    # Admin kontrolü
    is_anonymous = message.sender_chat is not None and user and user.id == 1087968824

    if is_anonymous:
        is_admin = can_anonymous_admin_use_commands(message)
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id) if user else False

    parts = lower_text.split(' ')

    if len(parts) == 1:
        # Sadece "roll" yazılmış - sessiz kal
        return

    command = ' '.join(parts[1:])

    # roll <sayı> - Roll başlat
    if command.isdigit():
        if not is_admin:
            return

        duration = int(command)
        await start_roll(chat.id, duration)
        await message.reply_text(
            ROLL["BASLADI"].format(duration=duration),
            parse_mode="HTML"
        )
        return

    # roll adım - Adım kaydet
    if command in ['adım', 'adim']:
        if not is_admin:
            return

        success, msg, step_number = await save_step(chat.id)

        if not success:
            await message.reply_text(msg, parse_mode="HTML")
            return

        # Adım listesini getir
        status, steps = await get_status_list(chat.id, return_raw=True)
        step_list = _format_steps(steps) if steps else ""

        await message.reply_text(
            ROLL["ADIM_KAYDEDILDI"].format(step=step_number, list=step_list),
            parse_mode="HTML"
        )
        return

    # roll mola - Mola başlat
    if command == 'mola':
        if not is_admin:
            return

        state = await get_roll_state(chat.id)

        if state['status'] == 'stopped':
            await message.reply_text(ROLL["AKTIF_DEGIL"], parse_mode="HTML")
            return

        if state['status'] in ['break', 'locked_break']:
            await message.reply_text(ROLL["ZATEN_MOLADA"], parse_mode="HTML")
            return

        was_locked = state['status'] == 'locked'

        await start_break(chat.id)

        if was_locked:
            await message.reply_text(ROLL["MOLA_BASLADI_KILITLI"], parse_mode="HTML")
        else:
            await message.reply_text(ROLL["MOLA_BASLADI"], parse_mode="HTML")
        return

    # roll devam - Moladan devam et
    if command == 'devam':
        if not is_admin:
            return

        state = await get_roll_state(chat.id)

        if state['status'] not in ['break', 'paused', 'locked_break']:
            await message.reply_text(ROLL["MOLA_YOK"], parse_mode="HTML")
            return

        was_locked_break = state['status'] == 'locked_break'

        success, new_status, duration = await resume_roll(chat.id)

        if was_locked_break or new_status == 'locked':
            await message.reply_text(
                ROLL["DEVAM_EDIYOR_KILITLI"].format(duration=duration),
                parse_mode="HTML"
            )
        else:
            await message.reply_text(
                ROLL["DEVAM_EDIYOR"].format(duration=duration),
                parse_mode="HTML"
            )
        return

    # roll kilit - Roll'u kilitle
    if command == 'kilit':
        if not is_admin:
            return

        state = await get_roll_state(chat.id)

        if state['status'] == 'stopped':
            await message.reply_text(ROLL["AKTIF_DEGIL"], parse_mode="HTML")
            return

        if state['status'] in ['locked', 'locked_break']:
            await message.reply_text(ROLL["ZATEN_KILITLI"], parse_mode="HTML")
            return

        was_break = state['status'] == 'break'

        await lock_roll(chat.id)

        if was_break:
            await message.reply_text(ROLL["KILITLENDI_MOLADA"], parse_mode="HTML")
        else:
            await message.reply_text(ROLL["KILITLENDI"], parse_mode="HTML")
        return

    # roll aç - Kilidi aç
    if command in ['aç', 'ac']:
        if not is_admin:
            return

        state = await get_roll_state(chat.id)

        if state['status'] not in ['locked', 'locked_break']:
            await message.reply_text(ROLL["KILITLI_DEGIL"], parse_mode="HTML")
            return

        success, prev_status = await unlock_roll(chat.id)

        if prev_status == 'break':
            await message.reply_text("🔓 Roll kilidi açıldı. Roll molada.", parse_mode="HTML")
        elif prev_status == 'paused':
            await message.reply_text("🔓 Roll kilidi açıldı. Roll duraklatılmış durumda.", parse_mode="HTML")
        else:
            await message.reply_text("🔓 Roll kilidi açıldı. Yeni kullanıcılar eklenebilir.", parse_mode="HTML")
        return

    # roll bitir - Roll'u sonlandır
    if command == 'bitir':
        if not is_admin:
            return

        state = await get_roll_state(chat.id)

        if state['status'] == 'stopped':
            await message.reply_text(ROLL["ZATEN_DURDURULMUS"], parse_mode="HTML")
            return

        # Önce temizlik yap
        await clean_inactive_users(chat.id)

        # Adım listesini al
        status, steps = await get_status_list(chat.id, return_raw=True)
        step_list = _format_steps(steps) if steps else ROLL["LISTE_BOS"]

        await stop_roll(chat.id)

        await message.reply_text(
            ROLL["SONLANDIRILDI"].format(list=step_list),
            parse_mode="HTML"
        )
        return


def _format_steps(steps: list) -> str:
    """Adımları formatla"""
    if not steps:
        return "📭 Kullanıcı yok."

    lines = []
    for step in steps:
        step_num = step['step_number']
        is_active = step.get('is_active', False)
        users = step.get('users', [])

        marker = "🔴 " if is_active else ""
        header = f"{marker}📍 Adım {step_num}"
        lines.append(header)

        if users:
            # Mesaj sayısına göre sırala
            sorted_users = sorted(users, key=lambda x: x.get('message_count', 0), reverse=True)
            for u in sorted_users:
                name = u.get('name', 'Kullanıcı')
                count = u.get('message_count', 0)
                lines.append(f"✅ {name} • {count} ✉️")
        else:
            lines.append("📭 Kullanıcı yok.")

        lines.append("")

    return "\n".join(lines)

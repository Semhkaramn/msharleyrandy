"""
📨 Mesaj Handler
Grup mesajlarını işler - Roll sistemi ve mesaj sayma
Özel mesajları işler - Randy ayarları
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
from services.randy_service import (
    track_post_randy_message, update_draft, get_draft,
    add_channel_to_draft
)
from utils.admin_check import is_group_admin, is_system_user, can_anonymous_admin_use_commands


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tüm mesajları işler:
    - Özel mesajlar: Randy ayarları
    - Grup mesajları: Roll komutları, mesaj sayma
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not message:
        return

    # ========== ÖZEL MESAJLAR (Randy ayarları) ==========
    if chat.type == 'private':
        await handle_private_message(update, context)
        return

    # ========== GRUP MESAJLARI ==========
    await handle_group_message(update, context)


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Özel mesajları işler - Randy ayarları"""
    user = update.effective_user
    message = update.effective_message

    if not message or not user:
        return

    waiting_for = context.user_data.get('waiting_for')

    if not waiting_for:
        return

    user_id = user.id

    # ========== RANDY MESAJI AYARLAMA ==========
    if waiting_for == 'randy_message':
        text = message.text or message.caption or ""

        if text:
            # İlk satır başlık, geri kalan mesaj
            lines = text.split('\n', 1)
            title = lines[0].strip()
            msg = lines[1].strip() if len(lines) > 1 else title

            await update_draft(user_id, title=title, message=msg)
            context.user_data.pop('waiting_for', None)

            await message.reply_text(
                f"✅ Randy mesajı ayarlandı!\n\n"
                f"<b>Başlık:</b> {title}\n"
                f"<b>Mesaj:</b> {msg}\n\n"
                f"Diğer ayarları yapmak için /randy yazın.",
                parse_mode="HTML"
            )
        return

    # ========== MESAJ SAYISI AYARLAMA ==========
    if waiting_for == 'randy_msg_count':
        text = message.text or ""

        try:
            count = int(text.strip())
            if count < 1:
                raise ValueError()

            await update_draft(user_id, required_message_count=count)
            context.user_data.pop('waiting_for', None)

            await message.reply_text(
                f"✅ Mesaj şartı ayarlandı: <b>{count}</b> mesaj\n\n"
                f"Diğer ayarları yapmak için /randy yazın.",
                parse_mode="HTML"
            )
        except ValueError:
            await message.reply_text(
                "❌ Geçerli bir sayı girin.\n\nÖrnek: 50",
                parse_mode="HTML"
            )
        return

    # ========== KANAL EKLEME ==========
    if waiting_for == 'randy_channels':
        text = message.text or ""
        text = text.strip()

        # Geç yazıldıysa
        if text.lower() == 'geç':
            context.user_data.pop('waiting_for', None)
            await message.reply_text(
                "✅ Kanal ekleme atlandı.\n\n"
                "Diğer ayarları yapmak için /randy yazın.",
                parse_mode="HTML"
            )
            return

        # @ ile başlayan username
        if text.startswith('@'):
            username = text[1:]  # @ işaretini kaldır
        else:
            username = text

        # Kanalı doğrula
        try:
            chat_info = await context.bot.get_chat(f"@{username}")

            if chat_info.type not in ['channel', 'supergroup']:
                await message.reply_text(
                    "❌ Bu bir kanal değil. Lütfen geçerli bir kanal username'i girin.\n\n"
                    "Örnek: @kanaladi",
                    parse_mode="HTML"
                )
                return

            # Kanalı taslağa ekle
            success, msg = await add_channel_to_draft(
                user_id,
                chat_info.id,
                username,
                chat_info.title
            )

            if success:
                await message.reply_text(
                    f"✅ Kanal eklendi: <b>{chat_info.title}</b> (@{username})\n\n"
                    f"Başka kanal eklemek için username gönderin veya /randy yazarak devam edin.",
                    parse_mode="HTML"
                )
            else:
                await message.reply_text(
                    f"⚠️ {msg}\n\nBaşka bir kanal deneyin veya /randy yazarak devam edin.",
                    parse_mode="HTML"
                )

        except TelegramError as e:
            await message.reply_text(
                f"❌ Kanal bulunamadı veya bota erişim yok.\n\n"
                f"Lütfen şunlara dikkat edin:\n"
                f"• Kanal public olmalı\n"
                f"• Bot kanalda admin olmalı\n"
                f"• Username doğru yazılmalı\n\n"
                f"Örnek: @kanaladi",
                parse_mode="HTML"
            )
        return

    # ========== MEDYA EKLEME ==========
    if waiting_for.startswith('randy_media_'):
        media_type = waiting_for.replace('randy_media_', '')
        file_id = None

        if media_type == 'photo' and message.photo:
            file_id = message.photo[-1].file_id
        elif media_type == 'video' and message.video:
            file_id = message.video.file_id
        elif media_type == 'animation' and message.animation:
            file_id = message.animation.file_id

        if file_id:
            await update_draft(user_id, media_file_id=file_id)
            context.user_data.pop('waiting_for', None)

            media_names = {'photo': 'Fotoğraf', 'video': 'Video', 'animation': 'GIF'}
            await message.reply_text(
                f"✅ {media_names.get(media_type, 'Medya')} eklendi!\n\n"
                f"Diğer ayarları yapmak için /randy yazın.",
                parse_mode="HTML"
            )
        else:
            media_names = {'photo': 'fotoğraf', 'video': 'video', 'animation': 'GIF'}
            await message.reply_text(
                f"❌ Lütfen bir {media_names.get(media_type, 'medya')} gönderin.",
                parse_mode="HTML"
            )
        return


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grup mesajlarını işler - Roll sistemi ve mesaj sayma"""
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

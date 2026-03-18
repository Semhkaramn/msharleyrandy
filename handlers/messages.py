"""
📨 Mesaj Handler
Grup mesajlarını işler - Roll sistemi ve mesaj sayma
Özel mesajları işler - Randy ayarları
"""

from telegram import Update


def turkish_lower(text: str) -> str:
    """
    Türkçe karakterleri düzgün küçük harfe çevirir.
    Python'un .lower() fonksiyonu Türkçe İ/I harflerini yanlış çevirir.
    """
    if not text:
        return ""
    # Türkçe karakter dönüşümleri
    tr_map = {
        'İ': 'i',
        'I': 'ı',
        'Ğ': 'ğ',
        'Ü': 'ü',
        'Ş': 'ş',
        'Ö': 'ö',
        'Ç': 'ç',
    }
    result = text
    for upper, lower in tr_map.items():
        result = result.replace(upper, lower)
    return result.lower()
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
    add_channel_to_draft, get_draft_channels,
    get_randy_by_message_id, get_participant_count, end_randy_with_count
)
from services.giveaway_service import (
    check_and_award_winner, get_giveaway_settings, update_giveaway_setting,
    create_giveaway, start_giveaway_watcher, update_announcement_message_id
)
from services.chat_control_service import close_chat, open_chat
from services.gpt_service import get_gpt_response, is_gpt_enabled, is_harley_mention
from utils.admin_check import is_group_admin, is_system_user, can_anonymous_admin_use_commands
from config import BOT_USERNAME
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from templates import MENU, BUTTONS, get_period_text, RANDY as RANDY_TEMPLATES, format_winner_list


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


async def _show_setup_menu_from_message(message, user_id: int, group_id: int, context):
    """Mesaj sonrası setup menüsünü göster - mümkünse mevcut mesajı düzenle"""
    draft = await get_draft(user_id, group_id)

    if not draft:
        await message.reply_text("❌ Taslak bulunamadı. /randy yazarak tekrar başlayın.")
        return

    # Kanalları getir (grup bazlı)
    channels = await get_draft_channels(user_id, group_id)

    # Durumu göster
    message_status = "✅" if draft.get('message') else "❌"

    # Şart durumu
    req_type = draft.get('requirement_type', 'none')
    req_count = draft.get('required_message_count', 0)
    if req_type != 'none' and req_count > 0:
        req_status = f"✅ ({get_period_text(req_type)} {req_count})"
    else:
        req_status = "➖"

    winner_count = draft.get('winner_count', 1)
    winner_status = f"({winner_count})"

    media_status = "✅" if draft.get('media_file_id') else "➖"
    pin_status = "✅" if draft.get('pin_message') else "❌"
    channel_status = f"✅ ({len(channels)})" if channels else "➖"

    keyboard = [
        [InlineKeyboardButton(f"{message_status} {BUTTONS['MESAJ_AYARLA']}", callback_data="randy_message")],
        [InlineKeyboardButton(f"{req_status} {BUTTONS['SART_AYARLA']}", callback_data="randy_requirement")],
        [InlineKeyboardButton(f"{BUTTONS['KAZANAN_AYARLA']} {winner_status}", callback_data="randy_winners")],
        [InlineKeyboardButton(f"{media_status} {BUTTONS['MEDYA_EKLE']}", callback_data="randy_media")],
        [InlineKeyboardButton(f"{channel_status} {BUTTONS['KANAL_EKLE']}", callback_data="randy_channels")],
        [InlineKeyboardButton(f"{pin_status} {BUTTONS['SABITLE']}", callback_data="randy_pin")],
        [
            InlineKeyboardButton(BUTTONS["ONIZLE"], callback_data="randy_preview"),
            InlineKeyboardButton(BUTTONS["KAYDET"], callback_data="randy_save")
        ],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    # Kayıtlı menü mesaj ID'si var mı kontrol et
    menu_message_id = context.user_data.get('menu_message_id')
    chat_id = message.chat.id

    if menu_message_id:
        try:
            # Mevcut mesajı düzenle
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text=MENU["RANDY_OLUSTUR"],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            # Kullanıcının gönderdiği mesajı sil
            try:
                await message.delete()
            except TelegramError:
                pass
            return
        except TelegramError:
            # Mesaj düzenlenemiyorsa yeni mesaj gönder
            pass

    # Yeni mesaj gönder ve ID'sini kaydet
    sent_msg = await message.reply_text(
        MENU["RANDY_OLUSTUR"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    context.user_data['menu_message_id'] = sent_msg.message_id


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
    group_id = context.user_data.get('active_group_id')  # Aktif grup ID'sini al

    # ========== RANDY MESAJI AYARLAMA ==========
    if waiting_for == 'randy_message':
        text = message.text or message.caption or ""

        if text:
            # Tüm metin direkt mesaj olarak kaydedilir (başlık yok)
            msg = text.strip()

            await update_draft(user_id, group_id=group_id, title="RANDY", message=msg)
            context.user_data.pop('waiting_for', None)

            # Menüye geri dön
            await _show_setup_menu_from_message(message, user_id, group_id, context)
        return

    # ========== MESAJ SAYISI AYARLAMA ==========
    if waiting_for == 'randy_msg_count':
        text = message.text or ""

        try:
            count = int(text.strip())
            if count < 1:
                raise ValueError()

            await update_draft(user_id, group_id=group_id, required_message_count=count)
            context.user_data.pop('waiting_for', None)

            # Menüye geri dön
            await _show_setup_menu_from_message(message, user_id, group_id, context)
        except ValueError:
            await message.reply_text(
                "❌ Geçerli bir sayı girin.\n\nÖrnek: 50",
                parse_mode="HTML"
            )
        return

    # ========== KAZANAN SAYISI AYARLAMA ==========
    if waiting_for == 'randy_winner_count':
        text = message.text or ""

        try:
            count = int(text.strip())
            if count < 1:
                raise ValueError()

            await update_draft(user_id, group_id=group_id, winner_count=count)
            context.user_data.pop('waiting_for', None)

            # Menüye geri dön
            await _show_setup_menu_from_message(message, user_id, group_id, context)
        except ValueError:
            await message.reply_text(
                "❌ Geçerli bir sayı girin.\n\nÖrnek: 3",
                parse_mode="HTML"
            )
        return

    # ========== KANAL EKLEME ==========
    if waiting_for == 'randy_channels':
        text = message.text or ""
        text = text.strip()

        # Geç/Tamam yazıldıysa menüye dön
        if text.lower() in ['geç', 'gec', 'tamam', 'bitti']:
            context.user_data.pop('waiting_for', None)
            await _show_setup_menu_from_message(message, user_id, group_id, context)
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
                chat_info.title,
                group_id
            )

            if success:
                await message.reply_text(
                    f"✅ Kanal eklendi: <b>{chat_info.title}</b> (@{username})\n\n"
                    f"Başka kanal eklemek için username gönderin veya 'tamam' yazın.",
                    parse_mode="HTML"
                )
            else:
                await message.reply_text(
                    f"⚠️ {msg}\n\nBaşka bir kanal deneyin veya 'tamam' yazın.",
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
    if waiting_for == 'randy_media':
        file_id = None
        media_type = None

        # Hangi tür medya gönderildiğini tespit et
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            file_id = message.video.file_id
            media_type = 'video'
        elif message.animation:
            file_id = message.animation.file_id
            media_type = 'animation'
        elif message.document:
            # Bazı GIF'ler document olarak geliyor (t.me linklerinden vs.)
            mime_type = message.document.mime_type or ""
            if mime_type.startswith('video/') or mime_type == 'image/gif':
                file_id = message.document.file_id
                media_type = 'animation'
        elif message.sticker:
            # Animated sticker'lar da kabul edilebilir
            if message.sticker.is_animated or message.sticker.is_video:
                file_id = message.sticker.file_id
                media_type = 'animation'

        if file_id and media_type:
            await update_draft(user_id, group_id=group_id, media_file_id=file_id, media_type=media_type)
            context.user_data.pop('waiting_for', None)

            # Menüye geri dön
            await _show_setup_menu_from_message(message, user_id, group_id, context)
        else:
            await message.reply_text(
                "❌ Lütfen bir fotoğraf, video veya GIF gönderin.\n\n"
                "Medya eklemek istemiyorsanız 'geç' yazın.",
                parse_mode="HTML"
            )
        return

    # Eski medya formatı için geriye uyumluluk
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
            await update_draft(user_id, group_id=group_id, media_file_id=file_id, media_type=media_type)
            context.user_data.pop('waiting_for', None)

            # Menüye geri dön
            await _show_setup_menu_from_message(message, user_id, group_id, context)
        else:
            media_names = {'photo': 'fotoğraf', 'video': 'video', 'animation': 'GIF'}
            await message.reply_text(
                f"❌ Lütfen bir {media_names.get(media_type, 'medya')} gönderin.",
                parse_mode="HTML"
            )
        return

    # ========== ÇEKİLİŞ ÖDÜL METNİ ==========
    if waiting_for == 'cekilis_prize':
        from config import ACTIVITY_GROUP_ID
        text = message.text or ""

        if not text.strip():
            await message.reply_text(
                "❌ Ödül metni boş olamaz. Lütfen tekrar deneyin.",
                parse_mode="HTML"
            )
            return

        # Ödül metnini kaydet
        context.user_data['cekilis_prize'] = text.strip()
        context.user_data.pop('waiting_for', None)

        # Ayarlardan varsayılan değerleri al
        settings = await get_giveaway_settings(ACTIVITY_GROUP_ID)

        if settings:
            duration = settings.get('default_duration_hours', 2)
            winner_count = settings.get('default_winner_count', 1)
        else:
            duration = 2
            winner_count = 1

        # Onay menüsünü göster
        # Not: Süre ve kazanan sayısı ayarlardan gelir, onay ekranında değiştirilemez
        keyboard = [
            [InlineKeyboardButton("✅ Çekilişi Başlat", callback_data="cekilis_confirm_start")],
            [InlineKeyboardButton("⚙️ Ayarları Değiştir", callback_data="cekilis_settings")],
            [InlineKeyboardButton("❌ İptal", callback_data="cekilis_menu")],
        ]

        menu_message_id = context.user_data.get('menu_message_id')

        confirm_text = (
            "🎁 <b>Çekiliş Önizleme</b>\n\n"
            f"🎯 <b>Ödül:</b> {text.strip()}\n"
            f"⏱️ <b>Süre:</b> {duration} saat\n"
            f"🏆 <b>Kazanan:</b> {winner_count} kişi\n\n"
            "Onaylıyor musunuz?"
        )

        if menu_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text=confirm_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                try:
                    await message.delete()
                except TelegramError:
                    pass
                return
            except TelegramError:
                pass

        sent_msg = await message.reply_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        context.user_data['menu_message_id'] = sent_msg.message_id
        return

    # ========== ÇEKİLİŞ YÖNETİM GRUBU ID ==========
    if waiting_for == 'cekilis_admin_group':
        from config import ACTIVITY_GROUP_ID
        text = message.text or ""

        try:
            admin_group_id = int(text.strip())

            # Grup geçerli mi kontrol et
            try:
                chat = await context.bot.get_chat(admin_group_id)
                if chat.type not in ['group', 'supergroup']:
                    raise ValueError("Not a group")
            except TelegramError:
                await message.reply_text(
                    "❌ Grup bulunamadı veya bota erişim yok.\n\n"
                    "Lütfen şunlara dikkat edin:\n"
                    "• Bot grupta admin olmalı\n"
                    "• Grup ID'si doğru olmalı",
                    parse_mode="HTML"
                )
                return

            await update_giveaway_setting(ACTIVITY_GROUP_ID, admin_group_id=admin_group_id)
            context.user_data.pop('waiting_for', None)

            await message.reply_text(
                f"✅ Yönetim grubu ayarlandı: <b>{chat.title}</b>",
                parse_mode="HTML"
            )

            # Ayarlar menüsüne dön
            from handlers.callbacks import show_cekilis_settings
            # Menü mesajını güncelle
            menu_message_id = context.user_data.get('menu_message_id')
            if menu_message_id:
                try:
                    # Fake query oluştur
                    class FakeQuery:
                        def __init__(self, message):
                            self.message = message

                        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                            await context.bot.edit_message_text(
                                chat_id=self.message.chat.id,
                                message_id=menu_message_id,
                                text=text,
                                reply_markup=reply_markup,
                                parse_mode=parse_mode
                            )

                    fake_query = FakeQuery(message)
                    await show_cekilis_settings(fake_query, user_id, context)
                except TelegramError:
                    pass

        except ValueError:
            await message.reply_text(
                "❌ Geçersiz grup ID'si. Sayı olmalı.\n\nÖrnek: <code>-1001234567890</code>",
                parse_mode="HTML"
            )
        return


async def _handle_randy_reply_end(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_message):
    """
    Admin Randy mesajına herhangi bir şekilde reply yaparsa Randy'yi bitir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not reply_message or not chat or not user:
        return False

    # Reply yapılan mesajdan Randy'yi bul
    randy = await get_randy_by_message_id(chat.id, reply_message.message_id)

    if not randy:
        return False  # Bu mesaj bir Randy değil

    if randy['status'] != 'active':
        return False  # Randy zaten bitmiş

    # Admin kontrolü
    is_anonymous = message.sender_chat is not None and user.id == 1087968824

    if is_anonymous:
        is_admin = can_anonymous_admin_use_commands(message)
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id)

    if not is_admin:
        return False  # Admin değil

    # Katılımcı sayısını al
    participant_count = await get_participant_count(randy['id'])
    winner_count = randy['winner_count']

    # Randy'yi bitir
    success, winners = await end_randy_with_count(randy['id'], winner_count)

    if not success:
        return True

    if not winners:
        text = RANDY_TEMPLATES["KAZANAN_YOK"]
    else:
        # Kazanan mesajı
        winner_list = format_winner_list(winners)

        # Katılımcı sayısı kazanandan az mı?
        if participant_count < winner_count:
            text = RANDY_TEMPLATES["BITTI_KATILIMCI_AZ"].format(
                participants=participant_count,
                winner_count=winner_count,
                winner_list=winner_list
            )
        else:
            text = RANDY_TEMPLATES["BITTI"].format(
                participants=participant_count,
                winner_list=winner_list
            )

    # Orijinal Randy mesajını düzenle
    try:
        if randy.get('media_file_id') and randy.get('media_type') != 'none':
            # Medyalı mesaj - caption düzenle
            await context.bot.edit_message_caption(
                chat_id=chat.id,
                message_id=randy['message_id'],
                caption=text,
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            # Sadece metin mesajı
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=randy['message_id'],
                text=text,
                reply_markup=None,
                parse_mode="HTML"
            )
    except TelegramError:
        # Mesaj düzenlenemezse yeni mesaj gönder
        await context.bot.send_message(chat.id, text, parse_mode="HTML")

    return True


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grup mesajlarını işler - Roll sistemi ve mesaj sayma"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not message:
        return

    # ========== RANDY REPLY BİTİRME KONTROLÜ ==========
    # Admin Randy mesajına herhangi bir şekilde reply yaparsa Randy'yi bitir
    if message.reply_to_message:
        handled = await _handle_randy_reply_end(update, context, message.reply_to_message)
        if handled:
            return  # Randy bitirildi, başka işlem yapma

    # ========== SİSTEM HESABI KONTROLÜ ==========
    text = message.text or ""
    lower_text = turkish_lower(text.strip()) if text else ""

    # Telegram servis hesabı (777000) - bağlı kanal mesajları
    if user and user.id in IGNORED_USER_IDS:
        return

    # Anonim admin kontrolü (GroupAnonymousBot - 1087968824)
    is_anonymous = message.sender_chat is not None and user and user.id == 1087968824

    # ========== İYİ GECELER / GÜNAYDIN HARLEY KOMUTLARI (Admin) ==========

    # "iyi geceler harley" veya "günaydın harley" kontrolü
    if lower_text in ['iyi geceler harley', 'iyi geceler harely', 'iyigeceler harley']:
        # Admin kontrolü
        if is_anonymous:
            is_admin = can_anonymous_admin_use_commands(message)
        else:
            is_admin = await is_group_admin(context.bot, chat.id, user.id) if user else False

        if is_admin:
            success, msg = await close_chat(context.bot, chat.id)
            await context.bot.send_message(chat.id, msg, parse_mode="HTML")
        return

    if lower_text in ['günaydın harley', 'gunaydin harley', 'günaydın harely', 'gunaydin harely']:
        # Admin kontrolü
        if is_anonymous:
            is_admin = can_anonymous_admin_use_commands(message)
        else:
            is_admin = await is_group_admin(context.bot, chat.id, user.id) if user else False

        if is_admin:
            success, msg = await open_chat(context.bot, chat.id)
            await context.bot.send_message(chat.id, msg, parse_mode="HTML")
        return

    # ========== GPT HARLEY SOHBET ==========
    # Harley'den bahsediliyorsa veya bot mesajına reply yapılıyorsa GPT ile cevap ver

    should_respond_gpt = False

    # 1. Harley'den bahsediliyor mu?
    if is_harley_mention(text):
        should_respond_gpt = True

    # 2. Bot mesajına reply yapılıyor mu?
    if message.reply_to_message:
        reply_from = message.reply_to_message.from_user
        if reply_from and reply_from.is_bot:
            # Kendi botumuz mu kontrol et
            bot_info = await context.bot.get_me()
            if reply_from.id == bot_info.id:
                should_respond_gpt = True

    if should_respond_gpt and text:
        # GPT bu grup için açık mı?
        gpt_enabled = await is_gpt_enabled(chat.id)

        if gpt_enabled:
            # Kullanıcı adını al
            user_name = user.first_name if user else "Kullanıcı"

            # GPT'den cevap al
            gpt_response = await get_gpt_response(text, user_name)

            if gpt_response:
                await message.reply_text(gpt_response)

            # GPT cevabı verdiyse mesaj sayma vs. devam etsin ama return etmesin

    # ========== ROLL KOMUTLARI (Admin) ==========

    # Text mesajı yoksa roll komutlarını atla
    if not text:
        # Mesaj sayma ve Randy takibi için devam et
        if user and not is_system_user(user.id) and not is_anonymous:
            await track_message(
                user.id, chat.id,
                user.username, user.first_name, user.last_name
            )
            await track_post_randy_message(
                chat.id, user.id,
                user.username, user.first_name
            )
        return

    # "liste" komutu
    if lower_text == 'liste':
        if is_anonymous:
            is_admin = can_anonymous_admin_use_commands(message)
        else:
            is_admin = await is_group_admin(context.bot, chat.id, user.id) if user else False

        if is_admin:
            status, steps, session_info = await get_status_list(chat.id, return_raw=True)
            if not steps and not session_info:
                await message.reply_text(ROLL["LISTE_BOS"], parse_mode="HTML")
            else:
                step_list = _format_steps(steps, session_info)
                await message.reply_text(step_list, parse_mode="HTML")
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
        # Bot kontrolü - botlar roll listesine eklenmez
        is_bot = user.is_bot if hasattr(user, 'is_bot') else False

        if not is_bot:
            # Admin kontrolü - adminler roll listesine eklenmez
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

    # 4. Çekiliş kazanan kontrolü
    await check_giveaway_winner(
        chat.id, user_id,
        username, first_name,
        message, context
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
        status, steps, session_info = await get_status_list(chat.id, return_raw=True)
        step_list = _format_steps(steps, session_info) if steps else ""

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
        status, steps, session_info = await get_status_list(chat.id, return_raw=True)
        step_list = _format_steps(steps, session_info) if steps else ROLL["LISTE_BOS"]

        await stop_roll(chat.id)

        await message.reply_text(
            ROLL["SONLANDIRILDI"].format(list=step_list),
            parse_mode="HTML"
        )
        return


async def check_giveaway_winner(
    group_id: int,
    user_id: int,
    username: str,
    first_name: str,
    message,
    context
):
    """
    Çekiliş kazanan kontrolü
    Kazanma zamanı geldiyse ve bu kullanıcı ilk mesaj yazıyorsa kazanır
    """
    from services.giveaway_service import (
        check_and_award_winner, get_giveaway_settings,
        update_slot_reply_message_id
    )
    from templates import GIVEAWAY

    try:
        # Bot kontrolü
        is_bot = message.from_user.is_bot if message.from_user else False

        # Kazanan kontrolü yap
        result = await check_and_award_winner(
            group_id=group_id,
            user_id=user_id,
            username=username,
            first_name=first_name,
            message_id=message.message_id,
            bot=context.bot,
            is_bot=is_bot
        )

        if not result:
            return  # Kazanan yok

        # KAZANDI!
        slot = result['slot']
        giveaway = result['giveaway']
        prize_text = result['prize_text']
        slot_number = slot['slot_number']
        total_winners = giveaway['winner_count']

        # Kazanma zamanını formatla
        from datetime import timezone
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo

        TR_TZ = ZoneInfo("Europe/Istanbul")
        won_at = slot.get('win_time')
        if won_at:
            if won_at.tzinfo is None:
                won_at = won_at.replace(tzinfo=timezone.utc)
            local_time = won_at.astimezone(TR_TZ)
            time_str = local_time.strftime("%H:%M")
        else:
            time_str = "??:??"

        # Kazanan mesajına reply at
        winner_text = GIVEAWAY["WINNER_MESSAGE"].format(
            prize=prize_text,
            slot=slot_number,
            total=total_winners,
            time=time_str
        )

        try:
            reply_msg = await message.reply_text(
                winner_text,
                parse_mode="HTML"
            )

            # Reply mesaj ID'sini kaydet
            await update_slot_reply_message_id(slot['id'], reply_msg.message_id)

            # Sabitleme
            if result.get('pin_winner_message', True):
                try:
                    await context.bot.pin_chat_message(
                        group_id,
                        reply_msg.message_id,
                        disable_notification=True
                    )
                except TelegramError:
                    pass

        except TelegramError as e:
            print(f"❌ Kazanan mesajı gönderme hatası: {e}")

        # Yönetim grubuna bildirim
        if result.get('notify_admin_group', True):
            settings = await get_giveaway_settings(group_id)

            if settings and settings.get('admin_group_id'):
                admin_group_id = settings['admin_group_id']

                # Kullanıcı mention'ı
                winner_mention = f'<a href="tg://user?id={user_id}">{first_name}</a>'

                # Grup adını al
                try:
                    group_chat = await context.bot.get_chat(group_id)
                    group_name = group_chat.title or f"Grup {group_id}"
                except TelegramError:
                    group_name = f"Grup {group_id}"

                admin_text = GIVEAWAY["ADMIN_NOTIFICATION"].format(
                    winner_mention=winner_mention,
                    prize=prize_text,
                    slot=slot_number,
                    total=total_winners,
                    time=time_str,
                    group_name=group_name
                )

                try:
                    admin_msg = await context.bot.send_message(
                        admin_group_id,
                        admin_text,
                        parse_mode="HTML"
                    )

                    # Yönetimde sabitleme
                    if result.get('pin_in_admin_group', True):
                        try:
                            await context.bot.pin_chat_message(
                                admin_group_id,
                                admin_msg.message_id,
                                disable_notification=True
                            )
                        except TelegramError:
                            pass

                except TelegramError as e:
                    print(f"❌ Admin bildirim hatası: {e}")

    except Exception as e:
        print(f"❌ Çekiliş kazanan kontrolü hatası: {e}")


def _format_steps(steps: list, session_info: dict = None) -> str:
    """Adımları formatla - roll durumu ve başlama saati ile"""
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    lines = []

    # Session bilgisi varsa başlangıçta göster
    if session_info:
        status = session_info.get('status', '')
        created_at = session_info.get('created_at')
        duration = session_info.get('active_duration', 0)

        # Durum metni
        status_texts = {
            'active': '🟢 Aktif',
            'paused': '⏸️ Duraklatıldı',
            'stopped': '🔴 Durduruldu',
            'break': '☕ Mola',
            'locked': '🔒 Kilitli',
            'locked_break': '🔒☕ Kilitli Mola'
        }
        status_text = status_texts.get(status, status)

        lines.append(f"📊 <b>Roll Durumu:</b> {status_text}")

        # Başlama saati - düzgün timezone dönüşümü
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            local_time = created_at.astimezone(TR_TZ)
            time_str = local_time.strftime("%d.%m.%Y %H:%M")
            lines.append(f"🕐 <b>Başlama Saati:</b> {time_str}")

        # Süre kuralı
        if duration:
            lines.append(f"⏳ <b>Süre Kuralı:</b> {duration} dakika")

        lines.append("")  # Boşluk

    if not steps:
        lines.append("📭 Kullanıcı yok.")
        return "\n".join(lines)

    for step in steps:
        step_num = step['step_number']
        is_active = step.get('is_active', False)
        users = step.get('users', [])
        step_created_at = step.get('created_at')

        marker = "🔴 " if is_active else ""
        header = f"{marker}📍 Adım {step_num}"

        # Adım başlama saatini ekle - düzgün timezone dönüşümü
        if step_created_at:
            if step_created_at.tzinfo is None:
                step_created_at = step_created_at.replace(tzinfo=timezone.utc)
            local_time = step_created_at.astimezone(TR_TZ)
            step_time_str = local_time.strftime("%H:%M")
            header += f" ({step_time_str})"

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

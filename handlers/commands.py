"""
📝 Komut Handler'ları
Telegram bot komutlarını işler
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from database import db
from templates import MENU, STATS, BUTTONS, ERRORS
from services.message_service import get_user_stats
from services.randy_service import (
    get_active_randy, start_randy, end_randy,
    register_group, update_group_admin, get_user_admin_groups,
    get_group_draft, get_randy_by_message_id, end_randy_with_count, get_participant_count,
    update_randy_winner_count, update_draft_winner_count, get_randy_channels,
    get_or_create_group_draft
)
from utils.admin_check import is_group_admin, is_system_user, can_anonymous_admin_use_commands, is_activity_group_admin


async def _handle_randy_reply_end(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_message):
    """
    Reply ile Randy bitirme
    Admin, Randy mesajına reply yaparak Randy'yi bitirebilir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not reply_message or not chat or not user:
        return

    # Reply yapılan mesajdan Randy'yi bul
    from services.randy_service import get_randy_by_message_id
    randy = await get_randy_by_message_id(chat.id, reply_message.message_id)

    if not randy:
        return  # Bu mesaj bir Randy değil

    if randy['status'] != 'active':
        info_msg = await context.bot.send_message(
            chat.id,
            "⚠️ Bu Randy zaten bitmiş.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(3)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Katılımcı sayısını al
    participant_count = await get_participant_count(randy['id'])
    winner_count = randy['winner_count']

    # Randy'yi bitir (varsayılan kazanan sayısı ile)
    from templates import RANDY as RANDY_TEMPLATES, format_winner_list

    success, winners = await end_randy_with_count(randy['id'], winner_count)

    if not success:
        return

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
            await context.bot.edit_message_caption(
                chat_id=chat.id,
                message_id=randy['message_id'],
                caption=text,
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=randy['message_id'],
                text=text,
                reply_markup=None,
                parse_mode="HTML"
            )
    except TelegramError:
        await context.bot.send_message(chat.id, text, parse_mode="HTML")


# ============================================
# /start - Bot Başlat
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start komutu
    - Özel mesajda: Ana menüyü göster (sadece adminler)
    - Grupta: Grubu kaydet
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user:
        return

    # Grupta /start
    if chat.type in ['group', 'supergroup']:
        # Grubu veritabanına kaydet
        await register_group(chat.id, chat.title or "")

        # Komutu göndereni admin olarak kaydet (admin kontrolü yapılacak)
        try:
            is_admin = await is_group_admin(context.bot, chat.id, user.id)
            await update_group_admin(chat.id, user.id, is_admin)
        except TelegramError:
            pass

        return

    # Özel mesajda /start - Önce admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user.id)

    if not is_admin:
        await message.reply_text(
            "❌ <b>Erişim Engellendi</b>\n\n"
            "Bu botu kullanmak için ana gruptaki admin olmanız gerekiyor.\n\n"
            "💡 <i>Eğer admin olduğunuzu düşünüyorsanız, önce grupta /start yazarak kendinizi kaydedin.</i>",
            parse_mode="HTML"
        )
        return

    # Admin ise direkt Randy ayar menüsüne yönlendir
    from services.randy_service import get_or_create_group_draft, get_user_admin_groups, register_group, update_group_admin
    from config import ACTIVITY_GROUP_ID

    # Admin olduğu grupları getir
    groups = await get_user_admin_groups(user.id, context.bot)

    # ACTIVITY_GROUP_ID tanımlı ama gruplar boşsa, grubu kaydet
    if not groups and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            chat_info = await context.bot.get_chat(ACTIVITY_GROUP_ID)
            await register_group(ACTIVITY_GROUP_ID, chat_info.title)
            await update_group_admin(ACTIVITY_GROUP_ID, user.id, True)

            groups = [{
                'group_id': ACTIVITY_GROUP_ID,
                'title': chat_info.title or f"Grup {ACTIVITY_GROUP_ID}"
            }]
        except Exception as e:
            print(f"❌ Grup bilgisi alma hatası: {e}")

    if not groups:
        await message.reply_text(
            "❌ <b>Admin olduğunuz grup bulunamadı.</b>\n\n"
            "Bu sorunu çözmek için:\n"
            "1️⃣ Bot'u gruba ekleyin\n"
            "2️⃣ Bot'a admin yetkisi verin\n"
            "3️⃣ Grupta /start komutunu kullanın\n\n"
            "💡 <i>Bu işlemler bot'un sizi grup admini olarak tanımasını sağlar.</i>",
            parse_mode="HTML"
        )
        return

    # Tek grup varsa direkt ayarlara git
    if len(groups) == 1:
        group = groups[0]
        group_id = group['group_id']

        # Grup için ayarları getir veya oluştur
        await get_or_create_group_draft(user.id, group_id)
        context.user_data['active_group_id'] = group_id

        # Ayar menüsünü göster
        from handlers.callbacks import show_setup_menu_message
        await show_setup_menu_message(message, user.id, group_id, context)
        return

    # Birden fazla grup varsa seçim menüsü göster
    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                group['title'] or f"Grup {group['group_id']}",
                callback_data=f"randy_group_{group['group_id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="randy_cancel")])

    await message.reply_text(
        MENU["RANDY_OLUSTUR_START"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ============================================
# /randy - Randy Ayarları (Özel)
# ============================================

async def randy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /randy komutu
    - Özel mesajda: Randy menüsünü aç
    - Grupta: Randy başlat (admin ise) - komut silinir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Grupta /randy - Randy başlat
    if chat.type in ['group', 'supergroup']:
        # Anonim admin kontrolü
        if can_anonymous_admin_use_commands(message):
            is_admin = True
        else:
            is_admin = await is_group_admin(context.bot, chat.id, user.id)

        if not is_admin:
            return

        # /randy komutunu sil
        try:
            await message.delete()
        except TelegramError:
            pass  # Silme yetkisi yoksa devam et

        # Reply ile Randy bitirme kontrolü
        if message.reply_to_message:
            await _handle_randy_reply_end(update, context, message.reply_to_message)
            return

        # Grup için ayarlar var mı?
        draft = await get_group_draft(chat.id)

        if not draft or not draft.get('message'):
            info_msg = await context.bot.send_message(
                chat.id,
                "❌ Bu grup için Randy ayarları yapılmamış.\n\n"
                "Önce özelden /start ile mesaj ayarlayın.",
                parse_mode="HTML"
            )
            # 5 saniye sonra sil
            import asyncio
            await asyncio.sleep(5)
            try:
                await info_msg.delete()
            except TelegramError:
                pass
            return

        # Randy başlat
        success, randy_data = await start_randy(chat.id, user.id)

        if not success:
            if randy_data and randy_data.get("error") == "already_active":
                info_msg = await context.bot.send_message(
                    chat.id,
                    "⚠️ Bu grupta zaten aktif bir Randy var.",
                    parse_mode="HTML"
                )
                import asyncio
                await asyncio.sleep(5)
                try:
                    await info_msg.delete()
                except TelegramError:
                    pass
            return

        # Randy mesajını oluştur
        from templates import RANDY as RANDY_TEMPLATES, get_period_text
        from services.randy_service import get_randy_channels
        from config import ACTIVITY_GROUP_ID

        # Zorunlu kanalları al (activity dahil)
        channels_list = []

        # Activity group'u ekle
        if ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
            try:
                activity_chat = await context.bot.get_chat(ACTIVITY_GROUP_ID)
                if activity_chat.username:
                    channels_list.append(f'<a href="https://t.me/{activity_chat.username}">{activity_chat.title or activity_chat.username}</a>')
                elif activity_chat.title:
                    channels_list.append(activity_chat.title)
            except:
                pass

        # Eklenen zorunlu kanalları al
        randy_channels = await get_randy_channels(randy_data['id'])
        for ch in randy_channels:
            if ch.get('channel_username'):
                title = ch.get('channel_title') or ch['channel_username']
                channels_list.append(f'<a href="https://t.me/{ch["channel_username"]}">{title}</a>')
            elif ch.get('channel_title'):
                channels_list.append(ch['channel_title'])

        # Kanal metni oluştur (alt alta)
        if channels_list:
            channels_text = "📢 <b>Zorunlu:</b>\n" + "\n".join(channels_list) + "\n\n"
        else:
            channels_text = ""

        # Şart varsa şartlı template kullan
        req_type = randy_data.get('requirement_type', 'none')
        req_count = randy_data.get('required_message_count', 0)

        if req_type != 'none' and req_count > 0:
            period_text = get_period_text(req_type)
            requirement = f"{period_text} {req_count} mesaj"
            text = RANDY_TEMPLATES["BASLADI_SARTLI"].format(
                message=randy_data['message'],
                requirement=requirement,
                channels_text=channels_text,
                participants=0,
                winners=randy_data['winner_count']
            )
        else:
            text = RANDY_TEMPLATES["BASLADI"].format(
                message=randy_data['message'],
                channels_text=channels_text,
                participants=0,
                winners=randy_data['winner_count']
            )

        keyboard = [[
            InlineKeyboardButton(
                f"🎉 Katıl (0)",
                callback_data=f"randy_join_{randy_data['id']}"
            )
        ]]

        # Medya varsa medyalı gönder
        if randy_data.get('media_file_id') and randy_data.get('media_type') != 'none':
            media_type = randy_data['media_type']
            file_id = randy_data['media_file_id']

            try:
                if media_type == 'photo':
                    sent_msg = await context.bot.send_photo(
                        chat.id,
                        photo=file_id,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                elif media_type == 'video':
                    sent_msg = await context.bot.send_video(
                        chat.id,
                        video=file_id,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                elif media_type == 'animation':
                    sent_msg = await context.bot.send_animation(
                        chat.id,
                        animation=file_id,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                else:
                    sent_msg = await context.bot.send_message(
                        chat.id,
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
            except TelegramError:
                sent_msg = await context.bot.send_message(
                    chat.id,
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
        else:
            sent_msg = await context.bot.send_message(
                chat.id,
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

        # Mesaj ID'sini kaydet
        from services.randy_service import update_randy_message_id
        await update_randy_message_id(randy_data['id'], sent_msg.message_id)

        # Sabitleme
        if randy_data.get('pin_message'):
            try:
                await context.bot.pin_chat_message(
                    chat.id,
                    sent_msg.message_id,
                    disable_notification=True
                )
            except TelegramError:
                pass

        return

    # Özel mesajda /randy - Randy menüsünü göster
    # Önce activity group admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user.id)

    if not is_admin:
        await message.reply_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Randy ayarları yapmak için ana gruptaki admin olmanız gerekiyor.",
            parse_mode="HTML"
        )
        return

    # Direkt Randy ayar menüsüne yönlendir
    from services.randy_service import get_or_create_group_draft, get_user_admin_groups, register_group, update_group_admin
    from config import ACTIVITY_GROUP_ID

    # Admin olduğu grupları getir
    groups = await get_user_admin_groups(user.id, context.bot)

    # ACTIVITY_GROUP_ID tanımlı ama gruplar boşsa, grubu kaydet
    if not groups and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            chat_info = await context.bot.get_chat(ACTIVITY_GROUP_ID)
            await register_group(ACTIVITY_GROUP_ID, chat_info.title)
            await update_group_admin(ACTIVITY_GROUP_ID, user.id, True)

            groups = [{
                'group_id': ACTIVITY_GROUP_ID,
                'title': chat_info.title or f"Grup {ACTIVITY_GROUP_ID}"
            }]
        except Exception as e:
            print(f"❌ Grup bilgisi alma hatası: {e}")

    if not groups:
        await message.reply_text(
            "❌ <b>Admin olduğunuz grup bulunamadı.</b>\n\n"
            "Bu sorunu çözmek için:\n"
            "1️⃣ Bot'u gruba ekleyin\n"
            "2️⃣ Bot'a admin yetkisi verin\n"
            "3️⃣ Grupta /start komutunu kullanın\n\n"
            "💡 <i>Bu işlemler bot'un sizi grup admini olarak tanımasını sağlar.</i>",
            parse_mode="HTML"
        )
        return

    # Tek grup varsa direkt ayarlara git
    if len(groups) == 1:
        group = groups[0]
        group_id = group['group_id']

        # Grup için ayarları getir veya oluştur
        await get_or_create_group_draft(user.id, group_id)
        context.user_data['active_group_id'] = group_id

        # Ayar menüsünü göster
        from handlers.callbacks import show_setup_menu_message
        await show_setup_menu_message(message, user.id, group_id, context)
        return

    # Birden fazla grup varsa seçim menüsü göster
    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                group['title'] or f"Grup {group['group_id']}",
                callback_data=f"randy_group_{group['group_id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="randy_cancel")])

    await message.reply_text(
        MENU["RANDY_OLUSTUR_START"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ============================================
# /number X - Kazanan Sayısı Değiştir (Grup)
# ============================================

async def number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /number X komutu - Kazanan sayısını değiştir
    Kullanım: /number 4 (kazanan sayısını 4 yapar)

    - Aktif Randy varsa: Randy mesajını günceller
    - Aktif Randy yoksa: Taslağı günceller (bir sonraki Randy bu sayıyla başlar)
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Sadece gruplarda çalışır
    if chat.type not in ['group', 'supergroup']:
        return

    # Admin kontrolü
    if can_anonymous_admin_use_commands(message):
        is_admin = True
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id)

    if not is_admin:
        return

    # /number komutunu sil
    try:
        await message.delete()
    except TelegramError:
        pass

    # Argüman kontrolü
    if not context.args or len(context.args) < 1:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Kullanım: /number X\n\nÖrnek: /number 4",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    try:
        winner_count = int(context.args[0])
        if winner_count < 1:
            raise ValueError("Kazanan sayısı en az 1 olmalı")
    except ValueError:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Geçerli bir sayı girin.\n\nÖrnek: /number 4",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Aktif Randy var mı?
    randy = await get_active_randy(chat.id)

    if not randy:
        # Aktif Randy yok - sadece taslağı güncelle
        # Önce taslağı oluştur/getir
        await get_or_create_group_draft(user.id, chat.id)
        # Taslağın kazanan sayısını güncelle
        await update_draft_winner_count(chat.id, winner_count)

        info_msg = await context.bot.send_message(
            chat.id,
            f"✅ Kazanan sayısı <b>{winner_count}</b> olarak ayarlandı.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Randy'nin kazanan sayısını güncelle
    await update_randy_winner_count(randy['id'], winner_count)

    # Taslağı da güncelle (gelecekteki randyler için)
    await update_draft_winner_count(chat.id, winner_count)

    # Katılımcı sayısını al
    participant_count = await get_participant_count(randy['id'])

    # Randy mesajını güncelle
    from templates import RANDY as RANDY_TEMPLATES, get_period_text
    from config import ACTIVITY_GROUP_ID

    # Zorunlu kanalları al (activity dahil)
    channels_list = []

    # Activity group'u ekle
    if ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            activity_chat = await context.bot.get_chat(ACTIVITY_GROUP_ID)
            if activity_chat.username:
                channels_list.append(f'<a href="https://t.me/{activity_chat.username}">{activity_chat.title or activity_chat.username}</a>')
            elif activity_chat.title:
                channels_list.append(activity_chat.title)
        except:
            pass

    # Eklenen zorunlu kanalları al
    randy_channels = await get_randy_channels(randy['id'])
    for ch in randy_channels:
        if ch.get('channel_username'):
            title = ch.get('channel_title') or ch['channel_username']
            channels_list.append(f'<a href="https://t.me/{ch["channel_username"]}">{title}</a>')
        elif ch.get('channel_title'):
            channels_list.append(ch['channel_title'])

    # Kanal metni oluştur (alt alta)
    if channels_list:
        channels_text = "📢 <b>Zorunlu:</b>\n" + "\n".join(channels_list) + "\n\n"
    else:
        channels_text = ""

    # Şart varsa şartlı template kullan
    req_type = randy.get('requirement_type', 'none')
    req_count = randy.get('required_message_count', 0)

    if req_type != 'none' and req_count > 0:
        period_text = get_period_text(req_type)
        requirement = f"{period_text} {req_count} mesaj"
        text = RANDY_TEMPLATES["BASLADI_SARTLI"].format(
            message=randy['message'],
            requirement=requirement,
            channels_text=channels_text,
            participants=participant_count,
            winners=winner_count
        )
    else:
        text = RANDY_TEMPLATES["BASLADI"].format(
            message=randy['message'],
            channels_text=channels_text,
            participants=participant_count,
            winners=winner_count
        )

    keyboard = [[
        InlineKeyboardButton(
            f"🎉 Katıl ({participant_count})",
            callback_data=f"randy_join_{randy['id']}"
        )
    ]]

    # Orijinal Randy mesajını düzenle
    try:
        if randy.get('media_file_id') and randy.get('media_type') != 'none':
            await context.bot.edit_message_caption(
                chat_id=chat.id,
                message_id=randy['message_id'],
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=randy['message_id'],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

        # Bildirim mesajı gönder
        import asyncio
        info_msg = await context.bot.send_message(
            chat.id,
            f"✅ Kazanan sayısı <b>{winner_count}</b> olarak güncellendi.",
            parse_mode="HTML"
        )
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass

    except TelegramError as e:
        print(f"❌ Randy mesajı güncelleme hatası: {e}")


# ============================================
# /bitir - Randy'yi Bitir (Grup)
# ============================================

async def bitir_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /bitir komutu - Aktif Randy'yi bitirir
    Randy mesajına reply yaparak veya direkt kullanılabilir
    Komut otomatik silinir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Sadece gruplarda çalışır
    if chat.type not in ['group', 'supergroup']:
        return

    # Admin kontrolü
    if can_anonymous_admin_use_commands(message):
        is_admin = True
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id)

    if not is_admin:
        return

    # Komutu sil
    try:
        await message.delete()
    except TelegramError:
        pass

    # Reply ile Randy bitirme
    if message.reply_to_message:
        randy = await get_randy_by_message_id(chat.id, message.reply_to_message.message_id)
        if randy and randy['status'] == 'active':
            await _finish_randy(context, chat.id, randy)
            return

    # Reply yoksa aktif Randy'yi bitir
    randy = await get_active_randy(chat.id)

    if not randy:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Bu grupta aktif Randy yok.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(3)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    await _finish_randy(context, chat.id, randy)


async def _finish_randy(context, chat_id: int, randy: dict):
    """Randy'yi bitir ve sonuçları orijinal mesajda göster"""
    from templates import RANDY as RANDY_TEMPLATES, format_winner_list

    participant_count = await get_participant_count(randy['id'])
    winner_count = randy['winner_count']

    success, winners = await end_randy_with_count(randy['id'], winner_count)

    if not success:
        return

    if not winners:
        text = RANDY_TEMPLATES["KAZANAN_YOK"]
    else:
        winner_list = format_winner_list(winners)

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
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=randy['message_id'],
                caption=text,
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=randy['message_id'],
                text=text,
                reply_markup=None,
                parse_mode="HTML"
            )
    except TelegramError:
        await context.bot.send_message(chat_id, text, parse_mode="HTML")


# ============================================
# .ben / !ben / /ben - Kullanıcı İstatistikleri
# ============================================

async def ben_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    .ben, !ben, /ben komutu - Kullanıcının mesaj istatistiklerini gösterir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Sadece gruplarda çalışır
    if chat.type not in ['group', 'supergroup']:
        return

    # Sistem hesapları için çalışmaz
    if is_system_user(user.id):
        return

    # Anonim admin kontrolü
    if message.sender_chat:
        await message.reply_text(
            "👤 <b>Anonim Admin</b>\n\n"
            "Anonim olarak mesaj gönderdiğiniz için istatistiklerinizi göremiyorum.\n\n"
            "💡 İstatistiklerinizi görmek için kendi hesabınızdan bu komutu kullanın.",
            parse_mode="HTML"
        )
        return

    # Kullanıcı istatistiklerini getir
    stats = await get_user_stats(user.id, chat.id)

    if not stats:
        name = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        await message.reply_text(
            STATS["KAYIT_YOK"],
            parse_mode="HTML"
        )
        return

    name = user.first_name or "Kullanıcı"

    text = STATS["ME"].format(
        name=name,
        daily=stats['daily'],
        weekly=stats['weekly'],
        monthly=stats['monthly'],
        total=stats['total']
    )

    await message.reply_text(text, parse_mode="HTML")


# ============================================
# .günlük - Günlük Sıralama (Admin)
# ============================================

async def gunluk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Günlük mesaj sıralaması (sadece adminler)"""
    await _leaderboard_command(update, context, 'daily')


async def haftalik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalık mesaj sıralaması (sadece adminler)"""
    await _leaderboard_command(update, context, 'weekly')


async def aylik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aylık mesaj sıralaması (sadece adminler)"""
    await _leaderboard_command(update, context, 'monthly')


async def _leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
    """Leaderboard komutu helper"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Sadece gruplarda çalışır
    if chat.type not in ['group', 'supergroup']:
        return

    # Admin kontrolü
    if can_anonymous_admin_use_commands(message):
        is_admin = True
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id)

    if not is_admin:
        return

    # Veritabanından sıralama al
    async with db.pool.acquire() as conn:
        if period == 'daily':
            field = 'daily_count'
            title = '📊 <b>Günlük Mesaj Sıralaması</b>'
            period_text = 'Bugünkü'
        elif period == 'weekly':
            field = 'weekly_count'
            title = '📊 <b>Haftalık Mesaj Sıralaması</b>'
            period_text = 'Bu hafta'
        else:
            field = 'monthly_count'
            title = '📅 <b>Aylık Mesaj Sıralaması</b>'
            period_text = 'Bu ay'

        users = await conn.fetch(f"""
            SELECT telegram_id, username, first_name, last_name, {field} as count
            FROM telegram_users
            WHERE group_id = $1 AND {field} > 0
            ORDER BY {field} DESC
            LIMIT 10
        """, chat.id)

    if not users:
        no_data = f"{title}\n\n⚠️ Henüz mesaj atan kullanıcı yok."
        await message.reply_text(no_data, parse_mode="HTML")
        return

    medals = ['🥇', '🥈', '🥉']
    lines = [title, ""]

    for i, u in enumerate(users):
        medal = medals[i] if i < 3 else f"{i + 1}."

        if u['username']:
            name = f"@{u['username']}"
        elif u['first_name']:
            name = u['first_name']
            if u['last_name']:
                name += f" {u['last_name']}"
        else:
            name = f"Kullanıcı {str(u['telegram_id'])[-4:]}"

        lines.append(f"{medal} {name} — <b>{u['count']}</b> mesaj")

    lines.append(f"\n💬 {period_text} en aktif {len(users)} kullanıcı")

    await message.reply_text("\n".join(lines), parse_mode="HTML")

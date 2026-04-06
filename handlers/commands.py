"""
📝 Komut Handler'ları
Telegram bot komutlarını işler
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from database import db
from templates import MENU, STATS, BUTTONS, ERRORS
from services.message_service import get_user_stats, get_full_user_stats, is_user_registered
from services.randy_service import (
    get_active_randy, start_randy, end_randy,
    register_group, update_group_admin, get_user_admin_groups,
    get_group_draft, get_randy_by_message_id, end_randy_with_count, get_participant_count,
    update_randy_winner_count, update_draft_winner_count, get_randy_channels,
    get_or_create_group_draft
)
from services.tagging_service import (
    start_etiket_tagging, start_naber_tagging, stop_tagging,
    is_tagging_active, get_tagging_type
)
from services.weekly_rewards_service import get_weekly_reward_settings
from services.activity_service import (
    get_activity_settings, get_leaderboard_with_rewards,
    get_activity_type_text, get_period_info, ACTIVITY_TYPES
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
    - stats_ parametresi ile: İstatistikleri göster
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

    # Özel mesajda /start - parametreleri kontrol et
    # stats_ parametresi ile geldiyse istatistikleri göster
    if context.args and len(context.args) > 0:
        arg = context.args[0]

        if arg.startswith("stats_"):
            # İstatistik isteği - kullanıcıya istatistiklerini göster
            # Format: stats_{group_id}
            try:
                group_id = int(arg.replace("stats_", ""))
            except ValueError:
                # Eski format veya hatalı - ACTIVITY_GROUP_ID kullan
                from config import ACTIVITY_GROUP_ID
                group_id = ACTIVITY_GROUP_ID

            if group_id:
                stats = await get_full_user_stats(user.id, group_id)

                if stats:
                    # İstatistik kartını oluştur
                    username_line = f"• @{user.username}" if user.username else ""

                    if stats.get('randy_participated', 0) > 0:
                        win_rate = (stats.get('randy_won', 0) / stats['randy_participated']) * 100
                        win_rate_line = f"┃ 📊 Oran                  <b>%{win_rate:.1f}</b>"
                    else:
                        win_rate_line = ""

                    text = STATS["USER_CARD"].format(
                        name=user.first_name or "Kullanıcı",
                        username_line=username_line,
                        daily=stats.get('daily', 0),
                        weekly=stats.get('weekly', 0),
                        monthly=stats.get('monthly', 0),
                        total=stats.get('total', 0),
                        randy_participated=stats.get('randy_participated', 0),
                        randy_won=stats.get('randy_won', 0),
                        win_rate_line=win_rate_line,
                        weekly_rank=stats.get('weekly_rank', '-'),
                        daily_avg=stats.get('daily_avg', 0)
                    )
                else:
                    text = STATS["KAYIT_YOK"]

                await message.reply_text(text, parse_mode="HTML")
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

    # Admin ise ANA MENÜ göster
    from handlers.callbacks import show_main_menu_message
    await show_main_menu_message(message, context)


# ============================================
# /randy - Grupta Randy Başlat
# ============================================

async def randy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /randy komutu
    - Özel mesajda: Ana menüye yönlendir (artık özel komut yok)
    - Grupta: Randy başlat (admin ise) - komut silinir
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Özel mesajda /randy çalışmaz - sessiz kal
    if chat.type == 'private':
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

        # Sadece ACTIVITY_GROUP_ID'de çalışır
        from config import ACTIVITY_GROUP_ID

        if ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0 and chat.id != ACTIVITY_GROUP_ID:
            # Bu grup activity group değil, sessizce çık
            return

        # Activity group için ayarlar var mı?
        # Önce chat.id ile dene, yoksa ACTIVITY_GROUP_ID ile dene
        draft = await get_group_draft(chat.id)

        if not draft and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
            draft = await get_group_draft(ACTIVITY_GROUP_ID)

        # Draft var mı ve içerik (mesaj veya medya) var mı kontrol et
        has_content = draft and (draft.get('message') or (draft.get('media_file_id') and draft.get('media_type') != 'none'))

        if not has_content:
            info_msg = await context.bot.send_message(
                chat.id,
                "❌ Randy ayarları yapılmamış.\n\n"
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
    .ben, !ben, /ben komutu - Kullanıcının istatistik kartını gösterir
    - Bot başlatılmışsa: Özelden istatistik gönderir ve grupta "Özelden gönderildi" yazar
    - Bot başlatılmamışsa: Grupta buton gösterir, tıklayınca botu başlatır ve özelden istatistik gönderir
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

    # Kullanıcı adını al - username öncelikli
    display_name = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{display_name}</a>'

    # Bot username'ini al
    from config import BOT_USERNAME
    bot_username = BOT_USERNAME or (await context.bot.get_me()).username

    # Kullanıcı botu başlatmış mı kontrol et
    bot_started = False
    try:
        # Özelden mesaj göndermeyi dene
        stats = await get_full_user_stats(user.id, chat.id)

        if stats:
            # İstatistik kartını oluştur
            username_line = f"• @{user.username}" if user.username else ""

            if stats.get('randy_participated', 0) > 0:
                win_rate = (stats.get('randy_won', 0) / stats['randy_participated']) * 100
                win_rate_line = f"┃ 📊 Oran                  <b>%{win_rate:.1f}</b>"
            else:
                win_rate_line = ""

            stats_text = STATS["USER_CARD"].format(
                name=user.first_name or "Kullanıcı",
                username_line=username_line,
                daily=stats.get('daily', 0),
                weekly=stats.get('weekly', 0),
                monthly=stats.get('monthly', 0),
                total=stats.get('total', 0),
                randy_participated=stats.get('randy_participated', 0),
                randy_won=stats.get('randy_won', 0),
                win_rate_line=win_rate_line,
                weekly_rank=stats.get('weekly_rank', '-'),
                daily_avg=stats.get('daily_avg', 0)
            )
        else:
            stats_text = STATS["KAYIT_YOK"]

        # Özelden istatistik gönder
        await context.bot.send_message(
            chat_id=user.id,
            text=stats_text,
            parse_mode="HTML"
        )
        bot_started = True

    except TelegramError:
        # Bot başlatılmamış
        bot_started = False

    if bot_started:
        # Bot başlatılmış - grupta "Özelden gönderildi" yaz (tıklanabilir link)
        await message.reply_text(
            f"👋 {mention}\n"
            f'📨 <a href="https://t.me/msharleybot">Özelden gönderildi</a>',
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    else:
        # Bot başlatılmamış - deep link butonu göster (tıklayınca botu başlatır ve direkt istatistik gösterir)
        deep_link = f"https://t.me/msharleybot?start=stats_{chat.id}"

        keyboard = [[
            InlineKeyboardButton(
                "📊 İstatistiklerimi Gör",
                url=deep_link
            )
        ]]

        await message.reply_text(
            f"👋 {mention}\n\n"
            "📊 İstatistiklerini görmek için aşağıdaki butona tıkla:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


# ============================================
# .bilgi / /bilgi - Kullanıcı Bilgisi (Admin)
# ============================================

async def bilgi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    .bilgi, /bilgi komutu - Hedef kullanıcının istatistik kartını gösterir
    SADECE ADMİNLER KULLANABİLİR
    Kullanım:
    - Reply ile: .bilgi (reply)
    - Username ile: .bilgi @username
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Sadece gruplarda çalışır
    if chat.type not in ['group', 'supergroup']:
        return

    # Admin kontrolü - SADECE ADMİNLER KULLANABİLİR
    if can_anonymous_admin_use_commands(message):
        is_admin = True
    else:
        is_admin = await is_group_admin(context.bot, chat.id, user.id)

    if not is_admin:
        return  # Admin değilse sessizce çık

    target_user = None
    target_id = None
    target_name = None
    target_username = None

    # Reply ile kullanım
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_id = target_user.id
        target_name = target_user.first_name or "Kullanıcı"
        target_username = target_user.username

    # @username ile kullanım - hem context.args hem de mesaj metninden parse et
    else:
        username_arg = None

        # Önce context.args'ı dene (CommandHandler ile)
        if context.args and len(context.args) > 0:
            username_arg = context.args[0].lstrip('@')
        else:
            # Regex ile yakalandıysa mesaj metninden parse et
            text = message.text or ""
            import re
            match = re.search(r'^[.!/]bilgi\s+@?(\w+)', text, re.IGNORECASE)
            if match:
                username_arg = match.group(1)

        if not username_arg:
            await message.reply_text(
                "❌ <b>Kullanım:</b>\n\n"
                "• Birine reply yaparak: <code>.bilgi</code>\n"
                "• Username ile: <code>.bilgi @username</code>",
                parse_mode="HTML"
            )
            return

        # Veritabanından kullanıcıyı bul
        try:
            from database import db
            async with db.pool.acquire() as conn:
                user_data = await conn.fetchrow("""
                    SELECT telegram_id, first_name, username
                    FROM telegram_users
                    WHERE group_id = $1 AND LOWER(username) = LOWER($2)
                    LIMIT 1
                """, chat.id, username_arg)

                if user_data:
                    target_id = user_data['telegram_id']
                    target_name = user_data['first_name'] or "Kullanıcı"
                    target_username = user_data['username']
                else:
                    await message.reply_text(
                        f"❌ @{username_arg} kullanıcısı bulunamadı.\n\n"
                        "💡 Kullanıcı grupta mesaj atmış olmalı.",
                        parse_mode="HTML"
                    )
                    return
        except Exception as e:
            print(f"❌ Kullanıcı arama hatası: {e}")
            await message.reply_text("❌ Bir hata oluştu.", parse_mode="HTML")
            return

    if not target_id:
        return

    # Tüm istatistikleri getir
    stats = await get_full_user_stats(target_id, chat.id)

    if not stats or (stats['total'] == 0 and stats['randy_participated'] == 0):
        await message.reply_text(
            f"📭 <b>{target_name}</b> için kayıt bulunamadı.",
            parse_mode="HTML"
        )
        return

    # İstatistik kartını oluştur
    text = _format_user_card(target_name, target_username, stats)
    await message.reply_text(text, parse_mode="HTML")


def _format_user_card(name: str, username: str, stats: dict) -> str:
    """İstatistik kartını formatla"""
    # Username satırı
    username_line = f"• @{username}" if username else ""

    # Kazanma oranı
    if stats['randy_participated'] > 0:
        win_rate = (stats['randy_won'] / stats['randy_participated']) * 100
        win_rate_line = f"┃ 📊 Oran                  <b>%{win_rate:.1f}</b>"
    else:
        win_rate_line = ""

    return STATS["USER_CARD"].format(
        name=name,
        username_line=username_line,
        daily=stats.get('daily', 0),
        weekly=stats.get('weekly', 0),
        monthly=stats.get('monthly', 0),
        total=stats.get('total', 0),
        randy_participated=stats.get('randy_participated', 0),
        randy_won=stats.get('randy_won', 0),
        win_rate_line=win_rate_line,
        weekly_rank=stats.get('weekly_rank', '-'),
        daily_avg=stats.get('daily_avg', 0)
    )


# ============================================
# .aktiflik - Aktivite Sıralaması (Admin)
# ============================================

async def aktiflik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    .aktiflik komutu - Aktivite sıralamasını gösterir
    SADECE ADMİNLER KULLANABİLİR

    Kullanım:
    - .aktiflik - Mevcut ayarlara göre sıralama gösterir
    - .aktiflik günlük - Günlük sıralama
    - .aktiflik haftalık - Haftalık sıralama
    - .aktiflik aylık - Aylık sıralama
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

    # Argümanı kontrol et
    text = message.text or ""
    activity_type = None

    if 'günlük' in text.lower() or 'gunluk' in text.lower():
        activity_type = 'daily'
    elif 'haftalık' in text.lower() or 'haftalik' in text.lower():
        activity_type = 'weekly'
    elif 'aylık' in text.lower() or 'aylik' in text.lower():
        activity_type = 'monthly'
    else:
        # Ayarlardan al
        settings = await get_activity_settings(chat.id)
        if settings:
            activity_type = settings.get('activity_type', 'weekly')
        else:
            activity_type = 'weekly'

    # Grup adminlerinin ID'lerini al
    admin_ids = []
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
    except TelegramError:
        pass

    # Sıralamayı ödüllerle birlikte al
    leaderboard = await get_leaderboard_with_rewards(chat.id, activity_type, admin_ids)

    if not leaderboard:
        type_text = get_activity_type_text(activity_type)
        await message.reply_text(
            f"📊 <b>{type_text} Aktivite Sıralaması</b>\n\n"
            f"⚠️ Henüz yeterli veri yok.",
            parse_mode="HTML"
        )
        return

    # Başlık oluştur
    type_text = get_activity_type_text(activity_type)
    period_info = get_period_info(activity_type)

    medals = ['🥇', '🥈', '🥉']
    lines = [
        f"📊 <b>{type_text} Aktivite Sıralaması</b>",
        f"📅 {period_info}",
        ""
    ]

    for user_data in leaderboard:
        rank = user_data['rank']
        medal = medals[rank - 1] if rank <= 3 else f"{rank}."
        telegram_id = user_data['telegram_id']

        # Görüntülenecek isim
        if user_data.get('username'):
            display_name = f"@{user_data['username']}"
        elif user_data.get('first_name'):
            display_name = user_data['first_name']
            if user_data.get('last_name'):
                display_name += f" {user_data['last_name']}"
        else:
            display_name = f"Kullanıcı {str(telegram_id)[-4:]}"

        name = f'<a href="tg://user?id={telegram_id}">{display_name}</a>'
        count = user_data.get('message_count', 0)
        reward = user_data.get('reward')

        if reward:
            lines.append(f"{medal} {name} - <b>{count}</b> - {reward}")
        else:
            lines.append(f"{medal} {name} - <b>{count}</b>")

    lines.append(f"\n💬 {type_text} en aktif {len(leaderboard)} kullanıcı")

    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ============================================
# .günlük - Günlük Sıralama (Admin)
# ============================================

async def gunluk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Günlük mesaj sıralaması (sadece adminler) - 20 kişi"""
    await _leaderboard_command(update, context, 'daily')


async def haftalik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalık mesaj sıralaması + ödüller (sadece adminler) - 20 kişi"""
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

    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")
    now_utc = datetime.now(timezone.utc)
    now_tr = now_utc.astimezone(TR_TZ)

    # Bu haftanın Pazartesi günü 00:00 (Türkiye saati) - UTC'ye çevir
    days_since_monday = now_tr.weekday()
    monday_tr = (now_tr - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
    period_start = monday_tr.astimezone(timezone.utc).replace(tzinfo=None)

    # Ödülleri al
    from services.weekly_rewards_service import get_rewards_for_group
    rewards = await get_rewards_for_group(chat.id)
    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}

    # Grup adminlerinin ID'lerini al (ödül listesinden hariç tutmak için)
    admin_ids = set()
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_ids = {admin.user.id for admin in admins}
    except TelegramError:
        pass

    # Admin ID'lerini liste olarak al
    admin_ids_list = list(admin_ids) if admin_ids else []

    async with db.pool.acquire() as conn:
        # Kullanıcıları getir (adminler hariç) - 20 kişi
        if admin_ids_list:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, last_name, weekly_count as count
                FROM telegram_users
                WHERE group_id = $1 AND weekly_count > 0 AND last_weekly_reset >= $2
                  AND telegram_id != ALL($3::BIGINT[])
                ORDER BY weekly_count DESC
                LIMIT 20
            """, chat.id, period_start, admin_ids_list)
        else:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, last_name, weekly_count as count
                FROM telegram_users
                WHERE group_id = $1 AND weekly_count > 0 AND last_weekly_reset >= $2
                ORDER BY weekly_count DESC
                LIMIT 20
            """, chat.id, period_start)

    if not users:
        no_data = "📊 <b>Haftalık Mesaj Sıralaması</b>\n\n⚠️ Henüz mesaj atan kullanıcı yok."
        await message.reply_text(no_data, parse_mode="HTML")
        return

    # Hafta bilgisi
    week_number = now_tr.isocalendar()[1]
    year = now_tr.year

    medals = ['🥇', '🥈', '🥉']
    lines = [f"📊 <b>Haftalık Mesaj Sıralaması</b>", ""]

    for i, u in enumerate(users):
        rank = i + 1
        medal = medals[i] if i < 3 else f"{rank}."
        telegram_id = u['telegram_id']

        # Görüntülenecek ismi belirle - username öncelikli
        if u['username']:
            display_name = f"@{u['username']}"
        elif u['first_name']:
            display_name = u['first_name']
            if u['last_name']:
                display_name += f" {u['last_name']}"
        else:
            display_name = f"Kullanıcı {str(telegram_id)[-4:]}"

        # Her zaman tıklanabilir mention kullan
        name = f'<a href="tg://user?id={telegram_id}">{display_name}</a>'

        # Ödül kontrolü yap
        reward = rewards_dict.get(rank)
        if reward:
            lines.append(f"{medal} {name} - <b>{u['count']}</b> - {reward}")
        else:
            lines.append(f"{medal} {name} - <b>{u['count']}</b>")

    lines.append(f"\n💬 Bu hafta en aktif {len(users)} kullanıcı")

    await message.reply_text("\n".join(lines), parse_mode="HTML")


async def aylik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aylık mesaj sıralaması (sadece adminler) - 20 kişi"""
    await _leaderboard_command(update, context, 'monthly')


async def _leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
    """Leaderboard komutu helper - 20 kişi gösterir"""
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
    # Türkiye saat dilimini al
    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")
    now_utc = datetime.now(timezone.utc)
    now_tr = now_utc.astimezone(TR_TZ)

    # Grup adminlerinin ID'lerini al (listeden hariç tutmak için)
    admin_ids = set()
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_ids = {admin.user.id for admin in admins}
    except TelegramError:
        pass

    async with db.pool.acquire() as conn:
        if period == 'daily':
            field = 'daily_count'
            reset_field = 'last_daily_reset'
            title = '📊 <b>Günlük Mesaj Sıralaması</b>'
            period_text = 'Bugünkü'
            # Bugünün başlangıcı (Türkiye saati 00:00) - UTC'ye çevir
            today_start_tr = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = today_start_tr.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            field = 'monthly_count'
            reset_field = 'last_monthly_reset'
            title = '📅 <b>Aylık Mesaj Sıralaması</b>'
            period_text = 'Bu ay'
            # Bu ayın 1'i 00:00 (Türkiye saati) - UTC'ye çevir
            month_start_tr = now_tr.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_start = month_start_tr.astimezone(timezone.utc).replace(tzinfo=None)

        # Admin ID'lerini liste olarak al
        admin_ids_list = list(admin_ids) if admin_ids else []

        # Sadece bu dönemde mesaj atmış kullanıcıları getir (adminler hariç) - 20 kişi
        if admin_ids_list:
            users = await conn.fetch(f"""
                SELECT telegram_id, username, first_name, last_name, {field} as count
                FROM telegram_users
                WHERE group_id = $1 AND {field} > 0 AND {reset_field} >= $2
                  AND telegram_id != ALL($3::BIGINT[])
                ORDER BY {field} DESC
                LIMIT 20
            """, chat.id, period_start, admin_ids_list)
        else:
            users = await conn.fetch(f"""
                SELECT telegram_id, username, first_name, last_name, {field} as count
                FROM telegram_users
                WHERE group_id = $1 AND {field} > 0 AND {reset_field} >= $2
                ORDER BY {field} DESC
                LIMIT 20
            """, chat.id, period_start)

    if not users:
        no_data = f"{title}\n\n⚠️ Henüz mesaj atan kullanıcı yok."
        await message.reply_text(no_data, parse_mode="HTML")
        return

    medals = ['🥇', '🥈', '🥉']
    lines = [title, ""]

    for i, u in enumerate(users):
        medal = medals[i] if i < 3 else f"{i + 1}."
        telegram_id = u['telegram_id']

        # Görüntülenecek ismi belirle - username öncelikli
        if u['username']:
            display_name = f"@{u['username']}"
        elif u['first_name']:
            display_name = u['first_name']
            if u['last_name']:
                display_name += f" {u['last_name']}"
        else:
            display_name = f"Kullanıcı {str(telegram_id)[-4:]}"

        # Her zaman tıklanabilir mention kullan
        name = f'<a href="tg://user?id={telegram_id}">{display_name}</a>'

        lines.append(f"{medal} {name} — <b>{u['count']}</b> mesaj")

    lines.append(f"\n💬 {period_text} en aktif {len(users)} kullanıcı")

    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ============================================
# /etiket - Toplu Etiketleme (5'erli)
# ============================================

async def etiket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /etiket [mesaj] komutu
    Gruptaki kayıtlı kullanıcıları 5'erli gruplar halinde etiketler
    Premium emoji destekli - kullanıcının gönderdiği premium emojiyi kullanır
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

    # Zaten aktif etiketleme var mı?
    if is_tagging_active(chat.id):
        info_msg = await context.bot.send_message(
            chat.id,
            "⚠️ Zaten aktif bir etiketleme işlemi var.\n"
            "Durdurmak için /dur yazın.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Mesajı al (komuttan sonraki kısım)
    # Premium emoji desteği için orijinal metni ve entity'leri al
    original_text = message.text or ""
    message_entities = message.entities or []

    if context.args:
        tag_message = " ".join(context.args)
    else:
        tag_message = "🎉 Selamlar!"

    # Etiketlemeyi başlat - premium emoji desteği ile
    success = await start_etiket_tagging(
        chat.id,
        tag_message,
        context.bot,
        message,
        custom_emoji_text=original_text,
        message_entities=message_entities
    )

    if not success:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Etiketleme başlatılamadı.\n"
            "Kayıtlı kullanıcı yok veya bir hata oluştu.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass


# ============================================
# /naber - Tek Tek Rastgele Mesajlarla Etiketleme
# ============================================

async def naber_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /naber komutu
    Gruptaki kayıtlı kullanıcıları tek tek rastgele mesajlarla etiketler
    Premium emoji destekli
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

    # Zaten aktif etiketleme var mı?
    if is_tagging_active(chat.id):
        info_msg = await context.bot.send_message(
            chat.id,
            "⚠️ Zaten aktif bir etiketleme işlemi var.\n"
            "Durdurmak için /dur yazın.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Naber etiketlemeyi başlat
    success = await start_naber_tagging(
        chat.id,
        context.bot,
        message
    )

    if not success:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Naber etiketlemesi başlatılamadı.\n"
            "Kayıtlı kullanıcı yok veya bir hata oluştu.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(5)
        try:
            await info_msg.delete()
        except TelegramError:
            pass


# ============================================
# /dur - Etiketlemeyi Durdur
# ============================================

async def dur_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /dur komutu
    Aktif etiketleme işlemini durdurur (/etiket veya /naber)
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

    # Aktif etiketleme var mı?
    tagging_type = get_tagging_type(chat.id)

    if not tagging_type:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Aktif etiketleme işlemi yok.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(3)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
        return

    # Etiketlemeyi durdur
    stopped = stop_tagging(chat.id)

    if stopped:
        type_text = "Etiketleme" if tagging_type == "etiket" else "Naber"
        info_msg = await context.bot.send_message(
            chat.id,
            f"🛑 {type_text} işlemi durduruldu.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(3)
        try:
            await info_msg.delete()
        except TelegramError:
            pass
    else:
        info_msg = await context.bot.send_message(
            chat.id,
            "❌ Durdurma işlemi başarısız.",
            parse_mode="HTML"
        )
        import asyncio
        await asyncio.sleep(3)
        try:
            await info_msg.delete()
        except TelegramError:
            pass

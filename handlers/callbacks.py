"""
🔘 Callback Handler
Buton tıklamalarını yönetir
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from templates import (
    MENU, RANDY, BUTTONS, ERRORS, SUCCESS,
    format_winner_list, get_period_text, get_media_type_text
)
from services.randy_service import (
    get_draft, update_draft,
    get_user_admin_groups, join_randy, get_participant_count,
    get_randy_by_id, end_randy,
    add_channel_to_draft, remove_channel_from_draft,
    get_draft_channels, clear_draft_channels,
    get_or_create_group_draft
)
from services.gpt_service import is_gpt_enabled, enable_gpt, disable_gpt
from utils.admin_check import is_group_admin, is_activity_group_admin


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana callback handler"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # Randy join callbackleri için answer'ı kendi içinde yapacağız (show_alert için)
    # Diğer tüm callbackler için hemen answer çağır
    if not data.startswith("randy_join_"):
        await query.answer()

    # Menü mesaj ID'sini kaydet (hep aynı mesajı düzenlemek için)
    if query.message:
        context.user_data['menu_message_id'] = query.message.message_id

    # ============================================
    # MENÜ KAPAT
    # ============================================
    if data == "close_menu":
        await close_menu(query, context)
        return

    # ============================================
    # ANA MENÜ
    # ============================================
    if data == "main_menu":
        await show_main_menu(query, context)

    # ============================================
    # RANDY MENÜSÜ - Direkt ayarlara git
    # ============================================
    elif data == "randy_menu":
        await start_randy_settings(query, user_id, context)

    elif data == "randy_settings":
        await start_randy_settings(query, user_id, context)

    elif data.startswith("randy_group_"):
        group_id = int(data.replace("randy_group_", ""))
        await select_group(query, user_id, group_id, context)

    elif data == "randy_message":
        await prompt_message(query, user_id, context)

    elif data == "randy_requirement":
        await show_requirement_menu(query, user_id, context)

    elif data.startswith("randy_req_"):
        req_type = data.replace("randy_req_", "")
        await select_requirement(query, user_id, req_type, context)

    elif data == "randy_msg_count":
        await prompt_message_count(query, user_id, context)

    elif data == "randy_winners":
        await show_winner_count_menu(query, user_id, context)

    elif data.startswith("randy_win_"):
        count = int(data.replace("randy_win_", ""))
        await select_winner_count(query, user_id, count, context)

    elif data == "randy_media":
        await show_media_menu(query, user_id, context)

    elif data.startswith("randy_media_"):
        media_type = data.replace("randy_media_", "")
        await select_media_type(query, user_id, media_type, context)

    elif data == "randy_channels":
        await show_channels_menu(query, user_id, context)

    elif data == "randy_channels_clear":
        await clear_channels(query, user_id, context)

    elif data.startswith("randy_channel_remove_"):
        channel_id = int(data.replace("randy_channel_remove_", ""))
        await remove_channel(query, user_id, channel_id, context)

    elif data == "randy_pin":
        await toggle_pin(query, user_id, context)

    elif data == "randy_preview":
        await show_preview(query, user_id, context)

    elif data == "randy_save":
        await save_draft(query, user_id, context)

    elif data == "randy_cancel":
        await cancel_and_go_main(query, user_id, context)

    elif data == "randy_back":
        await go_back_to_randy_settings(query, user_id, context)

    elif data.startswith("randy_join_"):
        randy_id = int(data.replace("randy_join_", ""))
        await handle_randy_join(query, user_id, randy_id, context)

    # ============================================
    # ROLL MENÜSÜ
    # ============================================
    elif data == "roll_menu":
        await show_roll_menu(query, context)

    # ============================================
    # ETİKET MENÜSÜ
    # ============================================
    elif data == "etiket_menu":
        await show_etiket_menu(query, user_id, context)

    elif data == "auto_tag_menu":
        await show_auto_tag_menu(query, user_id, context)

    elif data == "auto_tag_toggle":
        await toggle_auto_tag_setting(query, user_id, context)

    elif data.startswith("auto_tag_interval_"):
        interval = int(data.replace("auto_tag_interval_", ""))
        await set_auto_tag_interval(query, user_id, interval, context)

    # ============================================
    # GPT MENÜSÜ
    # ============================================
    elif data == "gpt_menu":
        await show_gpt_menu(query, user_id, context)

    elif data.startswith("gpt_toggle_"):
        group_id = int(data.replace("gpt_toggle_", ""))
        await toggle_gpt_for_group(query, user_id, group_id, context)

    # ============================================
    # İSTATİSTİKLER MENÜSÜ
    # ============================================
    elif data == "stats_menu":
        await show_stats_menu(query, context)

    # ============================================
    # BOT BAŞLATMA KONTROLÜ (.ben için)
    # ============================================
    elif data.startswith("check_started_"):
        target_user_id = int(data.replace("check_started_", ""))
        await handle_check_started(query, user_id, target_user_id, context)


# ============================================
# ANA MENÜ FONKSİYONLARI
# ============================================

async def close_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Menüyü kapat ve mesajı sil"""
    try:
        await query.message.delete()
    except TelegramError:
        # Silinemezse sadece düzenle
        try:
            await query.edit_message_text(
                "✅ Menü kapatıldı.",
                reply_markup=None,
                parse_mode="HTML"
            )
        except TelegramError:
            pass

    # Context'i temizle
    context.user_data.pop('menu_message_id', None)
    context.user_data.pop('active_group_id', None)
    context.user_data.pop('waiting_for', None)


async def show_main_menu(query, context: ContextTypes.DEFAULT_TYPE = None):
    """Ana menüyü göster"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["RANDY_YONETIMI"], callback_data="randy_menu")],
        [InlineKeyboardButton(BUTTONS["ROLL_YONETIMI"], callback_data="roll_menu")],
        [InlineKeyboardButton(BUTTONS["ETIKET_YONETIMI"], callback_data="etiket_menu")],
        [InlineKeyboardButton(BUTTONS["GPT_AYARLARI"], callback_data="gpt_menu")],
        [InlineKeyboardButton(BUTTONS["ISTATISTIKLER"], callback_data="stats_menu")],
        [InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="close_menu")],
    ]

    await query.edit_message_text(
        MENU["ANA_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_main_menu_message(message, context: ContextTypes.DEFAULT_TYPE):
    """Ana menüyü mesaj olarak göster (ilk kez)"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["RANDY_YONETIMI"], callback_data="randy_menu")],
        [InlineKeyboardButton(BUTTONS["ROLL_YONETIMI"], callback_data="roll_menu")],
        [InlineKeyboardButton(BUTTONS["ETIKET_YONETIMI"], callback_data="etiket_menu")],
        [InlineKeyboardButton(BUTTONS["GPT_AYARLARI"], callback_data="gpt_menu")],
        [InlineKeyboardButton(BUTTONS["ISTATISTIKLER"], callback_data="stats_menu")],
        [InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="close_menu")],
    ]

    sent_msg = await message.reply_text(
        MENU["ANA_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    context.user_data['menu_message_id'] = sent_msg.message_id


# ============================================
# RANDY MENÜ FONKSİYONLARI
# ============================================

async def show_randy_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy ana menüsünü göster"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["RANDY_AYARLARI"], callback_data="randy_settings")],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["RANDY_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def start_randy_settings(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy ayarlarını düzenle - önce activity group admin kontrolü"""
    from config import ACTIVITY_GROUP_ID

    # Activity group admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Randy ayarları için ana gruptaki admin olmanız gerekiyor.\n\n"
            "💡 <i>Bot'u gruba ekleyip admin yaptıktan sonra grupta /start komutunu kullanın.</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Admin olduğu grupları getir (bot instance'ı ile)
    groups = await get_user_admin_groups(user_id, context.bot)

    # ACTIVITY_GROUP_ID tanımlı ama gruplar boşsa, grubu kaydet
    if not groups and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            chat = await context.bot.get_chat(ACTIVITY_GROUP_ID)
            from services.randy_service import register_group, update_group_admin
            await register_group(ACTIVITY_GROUP_ID, chat.title)
            await update_group_admin(ACTIVITY_GROUP_ID, user_id, True)

            groups = [{
                'group_id': ACTIVITY_GROUP_ID,
                'title': chat.title or f"Grup {ACTIVITY_GROUP_ID}"
            }]
        except Exception as e:
            print(f"❌ Grup bilgisi alma hatası: {e}")

    if not groups:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Admin olduğunuz grup bulunamadı.</b>\n\n"
            "Bu sorunu çözmek için:\n"
            "1️⃣ Bot'u gruba ekleyin\n"
            "2️⃣ Bot'a admin yetkisi verin\n"
            "3️⃣ Grupta /start komutunu kullanın\n\n"
            "💡 <i>Bu işlemler bot'un sizi grup admini olarak tanımasını sağlar.</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Tek grup varsa direkt ayarlara git
    if len(groups) == 1:
        group = groups[0]
        group_id = group['group_id']

        # Grup için ayarları getir veya oluştur
        await get_or_create_group_draft(user_id, group_id)
        context.user_data['active_group_id'] = group_id

        # Ayar menüsünü göster
        await show_randy_settings_menu(query, user_id, group_id, context)
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

    keyboard.append([InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")])

    await query.edit_message_text(
        MENU["RANDY_OLUSTUR_START"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_group(query, user_id: int, group_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Grup seçildi - mevcut grup taslağını kontrol et"""
    draft = await get_or_create_group_draft(user_id, group_id)

    if not draft:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ Taslak oluşturulamadı. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Context'e aktif grup ID'sini kaydet
    context.user_data['active_group_id'] = group_id

    await show_randy_settings_menu(query, user_id, group_id, context)


async def show_randy_settings_menu(query, user_id: int, group_id: int, context: ContextTypes.DEFAULT_TYPE = None):
    """Randy ayar menüsünü göster (grup bazlı) - mevcut değerlerle"""
    draft = await get_draft(user_id, group_id)

    if not draft:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(ERRORS["GENEL"], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Kanalları getir (grup bazlı)
    channels = await get_draft_channels(user_id, group_id)

    # Durumu göster
    message_status = "✅" if draft.get('message') else "❌"

    # Şart durumu - detaylı göster
    req_type = draft.get('requirement_type', 'none')
    req_count = draft.get('required_message_count', 0)
    if req_type != 'none' and req_count > 0:
        period_text = get_period_text(req_type)
        req_status = f"✅ ({period_text} {req_count})"
    else:
        req_status = "➖"

    winner_count = draft.get('winner_count', 1)
    winner_status = f"({winner_count})"

    media_type = draft.get('media_type', 'none')
    media_status = "✅" if media_type != 'none' and draft.get('media_file_id') else "➖"

    pin_status = "✅" if draft.get('pin_message') else "❌"
    channel_status = f"✅ ({len(channels)})" if channels else "➖"

    # GPT durumunu kontrol et
    gpt_on = await is_gpt_enabled(group_id)
    gpt_status = "✅" if gpt_on else "❌"

    keyboard = [
        [InlineKeyboardButton(f"{message_status} {BUTTONS['MESAJ_AYARLA']}", callback_data="randy_message")],
        [InlineKeyboardButton(f"{req_status} {BUTTONS['SART_AYARLA']}", callback_data="randy_requirement")],
        [InlineKeyboardButton(f"{BUTTONS['KAZANAN_AYARLA']} {winner_status}", callback_data="randy_winners")],
        [InlineKeyboardButton(f"{media_status} {BUTTONS['MEDYA_EKLE']}", callback_data="randy_media")],
        [InlineKeyboardButton(f"{channel_status} {BUTTONS['KANAL_EKLE']}", callback_data="randy_channels")],
        [InlineKeyboardButton(f"{pin_status} {BUTTONS['SABITLE']}", callback_data="randy_pin")],
        [InlineKeyboardButton(BUTTONS["ONIZLE"], callback_data="randy_preview")],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["RANDY_OLUSTUR"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_setup_menu_message(message, user_id: int, group_id: int, context):
    """Randy ayar menüsünü mesaj olarak göster (tek grup için) - ilk defa"""
    draft = await get_draft(user_id, group_id)

    if not draft:
        draft = await get_or_create_group_draft(user_id, group_id)

    if not draft:
        await message.reply_text("❌ Ayarlar oluşturulamadı. Lütfen tekrar deneyin.")
        return

    # Kanalları getir
    channels = await get_draft_channels(user_id, group_id)

    # Durumu göster
    message_status = "✅" if draft.get('message') else "❌"

    # Şart durumu
    req_type = draft.get('requirement_type', 'none')
    req_count = draft.get('required_message_count', 0)
    if req_type != 'none' and req_count > 0:
        period_text = get_period_text(req_type)
        req_status = f"✅ ({period_text} {req_count})"
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
        [InlineKeyboardButton(BUTTONS["ONIZLE"], callback_data="randy_preview")],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    sent_msg = await message.reply_text(
        MENU["RANDY_OLUSTUR"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    # Menü mesaj ID'sini kaydet
    context.user_data['menu_message_id'] = sent_msg.message_id


async def prompt_message(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj girişi iste - mevcut değeri göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    current_value = ""
    if draft and draft.get('message'):
        current_msg = draft['message']
        # Uzun mesajları kısalt
        if len(current_msg) > 100:
            current_msg = current_msg[:100] + "..."
        current_value = f"<b>Mevcut mesaj:</b>\n<i>{current_msg}</i>\n\n"

    context.user_data['waiting_for'] = 'randy_message'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        MENU["MESAJ_AYARLA"].format(current_value=current_value),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_requirement_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Şart seçim menüsü - mevcut değeri göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    current_value = ""
    if draft:
        req_type = draft.get('requirement_type', 'none')
        req_count = draft.get('required_message_count', 0)
        if req_type != 'none' and req_count > 0:
            period_text = get_period_text(req_type)
            current_value = f"<b>Mevcut şart:</b> {period_text} {req_count} mesaj\n\n"
        else:
            current_value = "<b>Mevcut şart:</b> Şartsız\n\n"

    keyboard = [
        [InlineKeyboardButton(BUTTONS["SARTSIZ"], callback_data="randy_req_none")],
        [InlineKeyboardButton(BUTTONS["GUNLUK_MESAJ"], callback_data="randy_req_daily")],
        [InlineKeyboardButton(BUTTONS["HAFTALIK_MESAJ"], callback_data="randy_req_weekly")],
        [InlineKeyboardButton(BUTTONS["AYLIK_MESAJ"], callback_data="randy_req_monthly")],
        [InlineKeyboardButton(BUTTONS["TOPLAM_MESAJ"], callback_data="randy_req_all_time")],
        [InlineKeyboardButton(BUTTONS["RANDY_SONRASI"], callback_data="randy_req_post_randy")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        MENU["SART_SEC"].format(current_value=current_value),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_requirement(query, user_id: int, req_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Şart seçildi"""
    group_id = context.user_data.get('active_group_id')
    await update_draft(user_id, group_id=group_id, requirement_type=req_type)

    if req_type == 'none':
        # Mesaj sayısını da sıfırla
        await update_draft(user_id, group_id=group_id, required_message_count=0)
        await show_randy_settings_menu(query, user_id, group_id, context)
    else:
        # Mesaj sayısı iste
        await prompt_message_count(query, user_id, context)


async def prompt_message_count(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj sayısı iste - mevcut değeri göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    current_value = ""
    if draft and draft.get('required_message_count', 0) > 0:
        current_value = f"<b>Mevcut değer:</b> {draft['required_message_count']} mesaj\n\n"

    context.user_data['waiting_for'] = 'randy_msg_count'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        MENU["MESAJ_SAYISI_GIR"].format(current_value=current_value),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_winner_count_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kazanan sayısı - mevcut değeri göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    current_value = ""
    if draft:
        winner_count = draft.get('winner_count', 1)
        current_value = f"<b>Mevcut değer:</b> {winner_count} kişi\n\n"

    context.user_data['waiting_for'] = 'randy_winner_count'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        MENU["KAZANAN_SAYISI"].format(current_value=current_value),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_winner_count(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Kazanan sayısı seçildi"""
    group_id = context.user_data.get('active_group_id')
    await update_draft(user_id, group_id=group_id, winner_count=count)
    await show_randy_settings_menu(query, user_id, group_id, context)


async def show_media_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Medya menüsü - mevcut değeri göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    current_value = ""
    if draft:
        media_type = draft.get('media_type', 'none')
        if media_type != 'none' and draft.get('media_file_id'):
            media_text = get_media_type_text(media_type)
            current_value = f"<b>Mevcut medya:</b> {media_text} ekli\n\n"
        else:
            current_value = "<b>Mevcut medya:</b> Yok\n\n"

    context.user_data['waiting_for'] = 'randy_media'

    keyboard = [
        [InlineKeyboardButton("🗑️ Medyayı Kaldır", callback_data="randy_media_none")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        MENU["MEDYA_GONDER"].format(current_value=current_value),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_media_type(query, user_id: int, media_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Medya tipi seçildi - sadece none için kullanılır"""
    group_id = context.user_data.get('active_group_id')

    if media_type == 'none':
        await update_draft(user_id, group_id=group_id, media_type='none', media_file_id=None)
        await query.answer("✅ Medya kaldırıldı!", show_alert=True)
        context.user_data.pop('waiting_for', None)
        await show_randy_settings_menu(query, user_id, group_id, context)


async def show_channels_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kanal ekleme menüsü"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    if not draft:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(ERRORS["GENEL"], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Veritabanından kanalları getir
    channels = await get_draft_channels(user_id, group_id)

    if channels:
        channel_list = []
        for ch in channels:
            if ch.get('channel_username'):
                channel_list.append(f"• @{ch['channel_username']}")
            elif ch.get('channel_title'):
                channel_list.append(f"• {ch['channel_title']}")
            else:
                channel_list.append(f"• Kanal ID: {ch['channel_id']}")

        channel_text = "\n".join(channel_list)
        info_text = f"📢 <b>Eklenen Kanallar ({len(channels)}):</b>\n{channel_text}\n\n"
    else:
        info_text = "📢 <b>Henüz kanal eklenmedi.</b>\n\n"

    context.user_data['waiting_for'] = 'randy_channels'

    keyboard = []

    # Her kanal için silme butonu
    for ch in channels:
        if ch.get('channel_username'):
            btn_text = f"❌ @{ch['channel_username']}"
        else:
            btn_text = f"❌ {ch.get('channel_title', 'Kanal')}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"randy_channel_remove_{ch['channel_id']}")
        ])

    if channels:
        keyboard.append([InlineKeyboardButton("🗑️ Tüm Kanalları Temizle", callback_data="randy_channels_clear")])

    keyboard.append([InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")])

    await query.edit_message_text(
        f"{info_text}📝 Kanal eklemek için username gönderin:\n<i>Örnek: @kanaladi</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def clear_channels(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Tüm kanalları temizle"""
    group_id = context.user_data.get('active_group_id')
    await clear_draft_channels(user_id, group_id)
    await query.answer("✅ Tüm kanallar temizlendi!", show_alert=True)
    await show_channels_menu(query, user_id, context)


async def remove_channel(query, user_id: int, channel_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Tek kanal sil"""
    group_id = context.user_data.get('active_group_id')
    await remove_channel_from_draft(user_id, channel_id, group_id)
    await query.answer("✅ Kanal silindi!", show_alert=True)
    await show_channels_menu(query, user_id, context)


async def toggle_pin(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Sabitleme toggle"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    if draft:
        new_value = not draft.get('pin_message', False)
        await update_draft(user_id, group_id=group_id, pin_message=new_value)
        status = "açıldı" if new_value else "kapatıldı"
        await query.answer(f"📌 Sabitleme {status}!", show_alert=True)

    await show_randy_settings_menu(query, user_id, group_id, context)


async def show_preview(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Önizleme göster"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    if not draft:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(ERRORS["GENEL"], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    message = draft.get('message', 'Mesaj belirlenmedi')

    preview = f"🎉 <b>RANDY BAŞLADI!</b>\n\n{message}"

    # Şart bilgisi
    req_type = draft.get('requirement_type', 'none')
    if req_type != 'none':
        period_text = get_period_text(req_type)
        req_count = draft.get('required_message_count', 0)
        requirement = f"{period_text} {req_count} mesaj"
    else:
        requirement = "Şartsız"

    # Medya bilgisi
    media_type = draft.get('media_type', 'none')
    media = get_media_type_text(media_type)

    # Pin bilgisi
    pin = "Evet" if draft.get('pin_message') else "Hayır"

    # Kanal bilgisi
    channels = await get_draft_channels(user_id, group_id)
    if channels:
        channel_names = []
        for ch in channels:
            if ch.get('channel_username'):
                channel_names.append(f"@{ch['channel_username']}")
            else:
                channel_names.append(ch.get('channel_title', 'Kanal'))
        channel_info = ", ".join(channel_names)
    else:
        channel_info = "Yok"

    text = MENU["ONIZLEME"].format(
        preview=preview,
        group=f"Grup ID: {draft.get('group_id', 'Belirlenmedi')}",
        requirement=requirement,
        winners=draft.get('winner_count', 1),
        media=media,
        pin=pin
    )

    text += f"\n• Kanallar: {channel_info}"

    keyboard = [
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def save_draft(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Taslağı kaydet"""
    group_id = context.user_data.get('active_group_id')
    draft = await get_draft(user_id, group_id)

    if not draft:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(ERRORS["GENEL"], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Zorunlu alanları kontrol et
    if not draft.get('group_id'):
        await query.answer("❌ Grup seçilmedi!", show_alert=True)
        return

    if not draft.get('message'):
        await query.answer("❌ Mesaj zorunludur!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        "✅ <b>Randy ayarları kaydedildi!</b>\n\n"
        "Grupta <code>/randy</code> yazarak çekilişi başlatabilirsiniz.\n\n"
        "💡 <i>Ayarlar kalıcıdır - her seferinde yeniden ayarlamaya gerek yok.</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cancel_and_go_main(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Menüden çık ve ana menüye dön"""
    # Context'i temizle
    context.user_data.pop('active_group_id', None)
    context.user_data.pop('waiting_for', None)

    await show_main_menu(query, context)


async def go_back_to_randy_settings(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy ayarlarına geri dön"""
    context.user_data.pop('waiting_for', None)

    group_id = context.user_data.get('active_group_id')

    if group_id:
        await show_randy_settings_menu(query, user_id, group_id, context)
    else:
        await show_randy_menu(query, user_id, context)


# ============================================
# ROLL MENÜ FONKSİYONLARI
# ============================================

async def show_roll_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Roll menüsünü göster - komutlar ve açıklamalar"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["ROLL_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ============================================
# ETİKET MENÜ FONKSİYONLARI
# ============================================

async def show_etiket_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Etiket menüsünü göster - komutlar ve açıklamalar + otomatik etiket butonu"""
    from services.tagging_service import get_auto_tag_settings
    from config import ACTIVITY_GROUP_ID

    # Otomatik etiket durumunu kontrol et
    auto_tag_status = "❌ Kapalı"
    if ACTIVITY_GROUP_ID:
        settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)
        if settings and settings.get('enabled'):
            auto_tag_status = "✅ Açık"

    keyboard = [
        [InlineKeyboardButton(f"🤖 Otomatik Etiket ({auto_tag_status})", callback_data="auto_tag_menu")],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["ETIKET_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_auto_tag_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Otomatik etiket ayarları menüsü"""
    from services.tagging_service import get_auto_tag_settings
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="etiket_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Otomatik etiket ayarları için ana gruptaki admin olmanız gerekiyor.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="etiket_menu")]]
        await query.edit_message_text(
            "❌ <b>Grup Tanımlı Değil</b>\n\n"
            "ACTIVITY_GROUP_ID ayarlanmamış.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Mevcut ayarları getir
    settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)

    if settings:
        status = "✅ Açık" if settings.get('enabled') else "❌ Kapalı"
        interval = settings.get('interval_minutes', 60)
        tag_type = settings.get('tag_type', 'naber')
    else:
        status = "❌ Kapalı"
        interval = 60
        tag_type = "naber"

    # Durum butonu
    toggle_text = "🔴 Kapat" if settings and settings.get('enabled') else "🟢 Aç"

    keyboard = [
        [InlineKeyboardButton(f"{toggle_text}", callback_data="auto_tag_toggle")],
        [
            InlineKeyboardButton("30dk" + (" ✓" if interval == 30 else ""), callback_data="auto_tag_interval_30"),
            InlineKeyboardButton("1 saat" + (" ✓" if interval == 60 else ""), callback_data="auto_tag_interval_60"),
        ],
        [
            InlineKeyboardButton("2 saat" + (" ✓" if interval == 120 else ""), callback_data="auto_tag_interval_120"),
            InlineKeyboardButton("3 saat" + (" ✓" if interval == 180 else ""), callback_data="auto_tag_interval_180"),
        ],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="etiket_menu")],
    ]

    text = MENU["AUTO_TAG_MENU"].format(
        status=status,
        interval=interval,
        tag_type=tag_type.upper()
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def toggle_auto_tag_setting(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Otomatik etiketi aç/kapat"""
    from services.tagging_service import (
        get_auto_tag_settings, set_auto_tag_settings,
        start_auto_tagging, stop_auto_tagging
    )
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.answer("❌ Yetkiniz yok!", show_alert=True)
        return

    if not ACTIVITY_GROUP_ID:
        await query.answer("❌ Grup tanımlı değil!", show_alert=True)
        return

    # Mevcut ayarları getir
    settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)

    if settings and settings.get('enabled'):
        # Kapat
        await set_auto_tag_settings(ACTIVITY_GROUP_ID, enabled=False)
        stop_auto_tagging(ACTIVITY_GROUP_ID)
        await query.answer("🔴 Otomatik etiket kapatıldı!", show_alert=True)
    else:
        # Aç
        interval = settings.get('interval_minutes', 60) if settings else 60
        await set_auto_tag_settings(ACTIVITY_GROUP_ID, enabled=True, interval_minutes=interval)
        await start_auto_tagging(ACTIVITY_GROUP_ID, context.bot, interval)
        await query.answer("🟢 Otomatik etiket açıldı!", show_alert=True)

    # Menüyü yenile
    await show_auto_tag_menu(query, user_id, context)


async def set_auto_tag_interval(query, user_id: int, interval: int, context: ContextTypes.DEFAULT_TYPE):
    """Otomatik etiket aralığını ayarla"""
    from services.tagging_service import (
        get_auto_tag_settings, set_auto_tag_settings,
        start_auto_tagging, stop_auto_tagging, is_auto_tagging_active
    )
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.answer("❌ Yetkiniz yok!", show_alert=True)
        return

    if not ACTIVITY_GROUP_ID:
        await query.answer("❌ Grup tanımlı değil!", show_alert=True)
        return

    # Mevcut ayarları getir
    settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)
    enabled = settings.get('enabled', False) if settings else False

    # Yeni aralığı kaydet
    await set_auto_tag_settings(ACTIVITY_GROUP_ID, enabled=enabled, interval_minutes=interval)

    # Eğer aktifse, görevi yeniden başlat
    if enabled and is_auto_tagging_active(ACTIVITY_GROUP_ID):
        stop_auto_tagging(ACTIVITY_GROUP_ID)
        await start_auto_tagging(ACTIVITY_GROUP_ID, context.bot, interval)

    await query.answer(f"✅ Aralık {interval} dakika olarak ayarlandı!", show_alert=True)

    # Menüyü yenile
    await show_auto_tag_menu(query, user_id, context)


# ============================================
# GPT MENÜ FONKSİYONLARI
# ============================================

async def show_gpt_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """GPT ayarları menüsünü göster"""
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "GPT ayarları için ana gruptaki admin olmanız gerekiyor.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Admin olduğu grupları getir
    groups = await get_user_admin_groups(user_id, context.bot)

    # ACTIVITY_GROUP_ID tanımlı ama gruplar boşsa ekle
    if not groups and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            chat = await context.bot.get_chat(ACTIVITY_GROUP_ID)
            groups = [{'group_id': ACTIVITY_GROUP_ID, 'title': chat.title}]
        except:
            pass

    if not groups:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ Admin olduğunuz grup bulunamadı.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    keyboard = []

    for group in groups:
        group_id = group['group_id']
        title = group.get('title') or f"Grup {group_id}"

        # GPT durumunu kontrol et
        gpt_on = await is_gpt_enabled(group_id)
        status = "✅ Açık" if gpt_on else "❌ Kapalı"

        keyboard.append([
            InlineKeyboardButton(
                f"{title} - {status}",
                callback_data=f"gpt_toggle_{group_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")])

    await query.edit_message_text(
        MENU["GPT_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def toggle_gpt_for_group(query, user_id: int, group_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Grup için GPT'yi aç/kapat"""

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.answer("❌ Yetkiniz yok!", show_alert=True)
        return

    # Mevcut durumu kontrol et ve toggle et
    gpt_on = await is_gpt_enabled(group_id)

    if gpt_on:
        await disable_gpt(group_id)
        await query.answer("❌ GPT kapatıldı!", show_alert=True)
    else:
        await enable_gpt(group_id)
        await query.answer("✅ GPT açıldı!", show_alert=True)

    # Menüyü yenile
    await show_gpt_menu(query, user_id, context)


# ============================================
# İSTATİSTİKLER MENÜ FONKSİYONLARI
# ============================================

async def show_stats_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """İstatistikler menüsünü göster"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["STATS_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_check_started(query, user_id: int, target_user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Bot başlatma kontrolü - .ben komutu için
    Sadece hedef kullanıcı tıklarsa mesajı siler
    """
    # Sadece hedef kullanıcı tıklayabilir
    if user_id != target_user_id:
        await query.answer("Bu buton sana ait değil!", show_alert=True)
        return

    # Kullanıcı botu başlatmış mı kontrol et
    try:
        # Bot'a mesaj göndermeyi dene
        await context.bot.send_chat_action(user_id, "typing")

        # Mesajı sil
        try:
            await query.message.delete()
        except TelegramError:
            pass

        await query.answer("✅ Harika! Artık .ben komutunu kullanabilirsin.", show_alert=True)
    except TelegramError:
        # Kullanıcı botu henüz başlatmamış
        await query.answer("❌ Önce yukarıdaki 'Botu Başlat' butonuna tıkla!", show_alert=True)


# ============================================
# RANDY KATILIM
# ============================================

async def handle_randy_join(query, user_id: int, randy_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy'ye katılım"""
    from services.randy_service import get_randy_channels
    from config import ACTIVITY_GROUP_ID

    username = query.from_user.username
    first_name = query.from_user.first_name

    # Bot instance'ı da gönder (kanal kontrolü için)
    success, code = await join_randy(randy_id, user_id, username, first_name, context.bot)

    if success:
        await query.answer(RANDY["BASARIYLA_KATILDIN"], show_alert=True)

        # Katılımcı sayısını güncelle
        count = await get_participant_count(randy_id)
        randy = await get_randy_by_id(randy_id)

        if randy:
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
            randy_channels = await get_randy_channels(randy_id)
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
                new_text = RANDY["BASLADI_SARTLI"].format(
                    message=randy['message'],
                    requirement=requirement,
                    channels_text=channels_text,
                    participants=count,
                    winners=randy['winner_count']
                )
            else:
                new_text = RANDY["BASLADI"].format(
                    message=randy['message'],
                    channels_text=channels_text,
                    participants=count,
                    winners=randy['winner_count']
                )

            keyboard = [[
                InlineKeyboardButton(
                    f"🎉 Katıl ({count})",
                    callback_data=f"randy_join_{randy_id}"
                )
            ]]

            try:
                # Medya varsa caption güncelle, yoksa text güncelle
                if randy.get('media_file_id') and randy.get('media_type') != 'none':
                    await query.edit_message_caption(
                        caption=new_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                else:
                    await query.edit_message_text(
                        new_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
            except TelegramError:
                pass

    elif code == "zaten_katildi":
        await query.answer(RANDY["ZATEN_KATILDIN"], show_alert=True)

    elif code == "aktif_degil":
        await query.answer(RANDY["AKTIF_DEGIL"], show_alert=True)

    elif code.startswith("kanal_uyesi_degil:"):
        channels = code.split(":", 1)[1]
        await query.answer(
            RANDY["KANAL_UYESI_DEGIL"].format(channels=channels),
            show_alert=True
        )

    elif code.startswith("mesaj_sarti:"):
        parts = code.split(":")
        period = get_period_text(parts[1])
        required = parts[2]
        current = parts[3]

        await query.answer(
            RANDY["MESAJ_SARTI_KARSILANMADI"].format(
                period=period, required=required, current=current
            ),
            show_alert=True
        )

    elif code.startswith("post_randy:"):
        parts = code.split(":")
        required = parts[1]
        current = parts[2]

        await query.answer(
            RANDY["POST_RANDY_SARTI"].format(required=required, current=current),
            show_alert=True
        )

    else:
        await query.answer(ERRORS["GENEL"], show_alert=True)

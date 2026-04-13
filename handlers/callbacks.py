"""
🔘 Callback Handler
Buton tıklamalarını yönetir
"""

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from utils.logger import get_logger

logger = get_logger(__name__)

from templates import (
    MENU, RANDY, BUTTONS, ERRORS, SUCCESS, GIVEAWAY, STATS,
    format_winner_list, get_period_text, get_media_type_text,
    format_giveaway_win_times, format_giveaway_list, format_top_winners,
    format_rewards_list
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
from services.giveaway_service import (
    get_giveaway_settings, save_giveaway_settings, update_giveaway_setting,
    create_giveaway, get_active_giveaway, get_giveaway_by_id,
    get_giveaway_win_times, cancel_giveaway, get_past_giveaways,
    get_giveaway_winners, get_top_winners, start_giveaway_watcher,
    update_announcement_message_id
)
from utils.admin_check import is_group_admin, is_activity_group_admin


# ============================================
# CALLBACK ROUTER - Direkt Eşleşmeler
# ============================================
# Format: "callback_data": (handler_func_name, needs_user_id, extra_args)

DIRECT_CALLBACKS = {
    # Menü kontrolleri
    "close_menu": ("close_menu", False, None),
    "main_menu": ("show_main_menu", False, None),

    # Randy menüsü
    "randy_menu": ("start_randy_settings", True, None),
    "randy_settings": ("start_randy_settings", True, None),
    "randy_message": ("prompt_message", True, None),
    "randy_requirement": ("show_requirement_menu", True, None),
    "randy_msg_count": ("prompt_message_count", True, None),
    "randy_winners": ("show_winner_count_menu", True, None),
    "randy_media": ("show_media_menu", True, None),
    "randy_channels": ("show_channels_menu", True, None),
    "randy_channels_clear": ("clear_channels", True, None),
    "randy_pin": ("toggle_pin", True, None),
    "randy_preview": ("show_preview", True, None),
    "randy_save": ("save_draft", True, None),
    "randy_cancel": ("cancel_and_go_main", True, None),
    "randy_back": ("go_back_to_randy_settings", True, None),

    # Roll menüsü
    "roll_menu": ("show_roll_menu", False, None),

    # Etiket menüsü
    "etiket_menu": ("show_etiket_menu", True, None),
    "auto_tag_menu": ("show_auto_tag_menu", True, None),
    "auto_tag_toggle": ("toggle_auto_tag_setting", True, None),
    "tag_excluded_menu": ("show_tag_excluded_menu", True, None),
    "tag_excluded_add": ("prompt_add_excluded_user", True, None),

    # GPT menüsü
    "gpt_menu": ("show_gpt_menu", True, None),

    # İstatistikler
    "stats_menu": ("show_stats_menu", False, None),

    # Çekiliş menüsü
    "cekilis_menu": ("show_cekilis_menu", True, None),
    "cekilis_settings": ("show_cekilis_settings", True, None),
    "cekilis_active": ("show_active_cekilis", True, None),
    "cekilis_past": ("show_past_cekilisler", True, None),
    "cekilis_top_winners": ("show_top_winners", True, None),
    "cekilis_create": ("start_cekilis_create", True, None),
    "cekilis_cancel": ("cancel_active_cekilis", True, None),
    "cekilis_toggle_pin_ann": ("toggle_cekilis_setting", True, ("pin_announcement",)),
    "cekilis_toggle_pin_win": ("toggle_cekilis_setting", True, ("pin_winner_message",)),
    "cekilis_toggle_notify_admin": ("toggle_cekilis_setting", True, ("notify_admin_group",)),
    "cekilis_toggle_pin_admin": ("toggle_cekilis_setting", True, ("pin_in_admin_group",)),
    "cekilis_set_admin_group": ("prompt_admin_group", True, None),
    "cekilis_duration_menu": ("show_duration_menu", True, None),
    "cekilis_winners_menu": ("show_winners_menu", True, None),
    "cekilis_limit_menu": ("show_limit_menu", True, None),
    "cekilis_confirm_start": ("confirm_start_cekilis", True, None),

    # Aktivite ödül menüsü
    "activity_menu": ("show_activity_menu", True, None),
    "activity_settings": ("show_activity_settings", True, None),
    "activity_top_menu": ("show_activity_top_count_menu", True, None),
    "activity_top_custom": ("prompt_activity_top_custom", True, None),
    "activity_rewards_menu": ("show_activity_rewards_menu", True, None),
    "activity_set_all_rewards": ("prompt_all_activity_rewards", True, None),
    "activity_toggle": ("show_activity_toggle_confirm", True, None),
    "activity_toggle_confirm": ("toggle_activity", True, None),
    "activity_toggle_cancel": ("show_activity_menu", True, None),

    # Haftalık ödül (geriye uyumluluk)
    "weekly_rewards_menu": ("show_activity_menu", True, None),
    "weekly_rewards_top_menu": ("show_activity_top_count_menu", True, None),
}

# ============================================
# CALLBACK ROUTER - Pattern Eşleşmeleri
# ============================================
# Format: (regex_pattern, handler_func_name, value_type)

PATTERN_CALLBACKS = [
    # Randy patterns (grup ID'leri negatif olabilir)
    (r"^randy_group_(-?\d+)$", "select_group", "int"),
    (r"^randy_req_(.+)$", "select_requirement", "str"),
    (r"^randy_win_(\d+)$", "select_winner_count", "int"),
    (r"^randy_media_(.+)$", "select_media_type", "str"),
    (r"^randy_channel_remove_(-?\d+)$", "remove_channel", "int"),
    (r"^randy_join_(\d+)$", "handle_randy_join", "int"),

    # Etiket patterns
    (r"^auto_tag_interval_(\d+)$", "set_auto_tag_interval", "int"),
    (r"^tag_excluded_remove_(\d+)$", "remove_excluded_user_callback", "int"),

    # GPT patterns (grup ID'leri negatif olabilir)
    (r"^gpt_toggle_(-?\d+)$", "toggle_gpt_for_group", "int"),

    # Çekiliş patterns
    (r"^cekilis_set_duration_(\d+)$", "set_cekilis_duration", "int"),
    (r"^cekilis_set_winners_(\d+)$", "set_cekilis_winners", "int"),
    (r"^cekilis_set_limit_(\d+)$", "set_cekilis_limit", "int"),
    (r"^cekilis_detail_(\d+)$", "show_cekilis_detail", "int"),

    # Aktivite patterns
    (r"^activity_type_(.+)$", "set_activity_type", "str"),
    (r"^activity_top_(\d+)$", "set_activity_top_count", "int"),
    (r"^activity_set_reward_(\d+)$", "prompt_activity_reward", "int"),

    # Haftalık ödül patterns (geriye uyumluluk)
    (r"^weekly_rewards_top_(\d+)$", "set_activity_top_count", "int"),
    (r"^weekly_set_reward_(\d+)$", "prompt_activity_reward", "int"),

    # Kullanıcı işlemleri (grup ID'leri negatif olabilir)
    (r"^check_started_(\d+)$", "handle_check_started", "int"),
    (r"^ben_stats_(-?\d+)$", "handle_ben_stats", "int"),
]


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana callback handler - Router Pattern ile"""
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

    # 1. Direkt eşleşme kontrolü
    if data in DIRECT_CALLBACKS:
        handler_name, needs_user_id, extra_args = DIRECT_CALLBACKS[data]
        handler = globals()[handler_name]

        if extra_args:
            # Ekstra argümanlar varsa (örn: toggle_cekilis_setting)
            await handler(query, user_id, *extra_args, context)
        elif needs_user_id:
            await handler(query, user_id, context)
        else:
            await handler(query, context)
        return

    # 2. Pattern eşleşme kontrolü
    for pattern, handler_name, value_type in PATTERN_CALLBACKS:
        match = re.match(pattern, data)
        if match:
            handler = globals()[handler_name]
            value = match.group(1)

            # Değeri uygun tipe çevir
            if value_type == "int":
                value = int(value)

            await handler(query, user_id, value, context)
            return

    # 3. Bilinmeyen callback - loglama için
    logger.warning(f"⚠️ Bilinmeyen callback: {data}")


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


def _get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Ana menü keyboard'unu döndür - tek yerde tanımla"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(BUTTONS["RANDY_YONETIMI"], callback_data="randy_menu")],
        [InlineKeyboardButton(BUTTONS["CEKILIS_YONETIMI"], callback_data="cekilis_menu")],
        [InlineKeyboardButton("🏆 Aktivite Ödülleri", callback_data="activity_menu")],
        [InlineKeyboardButton(BUTTONS["ROLL_YONETIMI"], callback_data="roll_menu")],
        [InlineKeyboardButton(BUTTONS["ETIKET_YONETIMI"], callback_data="etiket_menu")],
        [InlineKeyboardButton(BUTTONS["GPT_AYARLARI"], callback_data="gpt_menu")],
        [InlineKeyboardButton(BUTTONS["ISTATISTIKLER"], callback_data="stats_menu")],
        [InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="close_menu")],
    ])


async def show_main_menu(query, context: ContextTypes.DEFAULT_TYPE = None):
    """Ana menüyü göster"""
    await query.edit_message_text(
        MENU["ANA_MENU"],
        reply_markup=_get_main_menu_keyboard(),
        parse_mode="HTML"
    )


async def show_main_menu_message(message, context: ContextTypes.DEFAULT_TYPE):
    """Ana menüyü mesaj olarak göster (ilk kez)"""
    sent_msg = await message.reply_text(
        MENU["ANA_MENU"],
        reply_markup=_get_main_menu_keyboard(),
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
            logger.error(f"❌ Grup bilgisi alma hatası: {e}")
            # Kullanıcıya hata durumunu bildir
            keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
            await query.edit_message_text(
                "⚠️ <b>Grup Erişim Sorunu</b>\n\n"
                "Bot ana gruba erişemedi. Lütfen:\n"
                "1️⃣ Bot'un grupta admin olduğundan emin olun\n"
                "2️⃣ Grupta /start komutunu çalıştırın\n"
                "3️⃣ Tekrar deneyin\n\n"
                f"<i>Hata: {str(e)[:100]}</i>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

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
    from services.tag_exclusion_service import get_excluded_users
    from config import ACTIVITY_GROUP_ID

    # Otomatik etiket durumunu kontrol et
    auto_tag_status = "❌ Kapalı"
    excluded_count = 0

    if ACTIVITY_GROUP_ID:
        settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)
        if settings and settings.get('enabled'):
            auto_tag_status = "✅ Açık"

        # Hariç tutulan kullanıcı sayısı
        excluded_users = await get_excluded_users(ACTIVITY_GROUP_ID)
        excluded_count = len(excluded_users)

    keyboard = [
        [InlineKeyboardButton(f"🤖 Otomatik Etiket ({auto_tag_status})", callback_data="auto_tag_menu")],
        [InlineKeyboardButton(f"🚫 Etiketlenmeyecekler ({excluded_count})", callback_data="tag_excluded_menu")],
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
        interval = settings.get('interval_minutes', 10)
        tag_type = settings.get('tag_type', 'naber')
    else:
        status = "❌ Kapalı"
        interval = 10
        tag_type = "naber"

    # Durum butonu
    toggle_text = "🔴 Kapat" if settings and settings.get('enabled') else "🟢 Aç"

    keyboard = [
        [InlineKeyboardButton(f"{toggle_text}", callback_data="auto_tag_toggle")],
        [
            InlineKeyboardButton("5dk" + (" ✓" if interval == 5 else ""), callback_data="auto_tag_interval_5"),
            InlineKeyboardButton("7dk" + (" ✓" if interval == 7 else ""), callback_data="auto_tag_interval_7"),
            InlineKeyboardButton("10dk" + (" ✓" if interval == 10 else ""), callback_data="auto_tag_interval_10"),
        ],
        [
            InlineKeyboardButton("15dk" + (" ✓" if interval == 15 else ""), callback_data="auto_tag_interval_15"),
            InlineKeyboardButton("20dk" + (" ✓" if interval == 20 else ""), callback_data="auto_tag_interval_20"),
            InlineKeyboardButton("30dk" + (" ✓" if interval == 30 else ""), callback_data="auto_tag_interval_30"),
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
        interval = settings.get('interval_minutes', 10) if settings else 10
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
# ETİKET HARİÇ TUTMA FONKSİYONLARI
# ============================================

async def show_tag_excluded_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Etiketlenmeyecek kullanıcılar menüsünü göster"""
    from services.tag_exclusion_service import get_excluded_users, format_excluded_users_list
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="etiket_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Bu ayarlar için ana gruptaki admin olmanız gerekiyor.",
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

    # Hariç tutulan kullanıcıları getir
    excluded_users = await get_excluded_users(ACTIVITY_GROUP_ID)

    # Kullanıcı listesi
    users_text = format_excluded_users_list(excluded_users)

    # Silme butonları oluştur
    keyboard = []

    # Kullanıcı silme butonları
    for user in excluded_users[:10]:  # Max 10 göster
        telegram_id = user['telegram_id']
        username = user.get('username')
        first_name = user.get('first_name')

        display = f"@{username}" if username else first_name or str(telegram_id)
        keyboard.append([
            InlineKeyboardButton(f"❌ {display}", callback_data=f"tag_excluded_remove_{telegram_id}")
        ])

    # Ekle butonu
    keyboard.append([InlineKeyboardButton("➕ Kullanıcı Ekle", callback_data="tag_excluded_add")])
    keyboard.append([InlineKeyboardButton(BUTTONS["GERI"], callback_data="etiket_menu")])

    text = (
        "🚫 <b>Etiketlenmeyecek Kullanıcılar</b>\n\n"
        f"{users_text}\n\n"
        "💡 <i>Bu listedeki kullanıcılar etiketleme işlemlerinde (</i><code>/etiket</code><i>, </i><code>/naber</code><i>, otomatik etiket) atlanır.</i>\n\n"
        "⚠️ <i>Username değişse bile ID kaydedildiği için doğru çalışır.</i>"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def prompt_add_excluded_user(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Hariç tutulacak kullanıcı için input iste"""
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.answer("❌ Yetkiniz yok!", show_alert=True)
        return

    context.user_data['waiting_for'] = 'tag_excluded_add'
    context.user_data['active_group_id'] = ACTIVITY_GROUP_ID

    keyboard = [[InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="tag_excluded_menu")]]

    await query.edit_message_text(
        "👤 <b>Etiketlenmeyecek Kullanıcı Ekle</b>\n\n"
        "Kullanıcının <b>@username</b> veya <b>user_id</b> bilgisini gönderin.\n\n"
        "💡 <i>Username gönderseniz bile sistem ID olarak kaydedecektir.</i>\n\n"
        "📝 <b>Örnekler:</b>\n"
        "• <code>@kullaniciadi</code>\n"
        "• <code>123456789</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def remove_excluded_user_callback(query, user_id: int, telegram_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Hariç tutma listesinden kullanıcı sil"""
    from services.tag_exclusion_service import remove_excluded_user
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.answer("❌ Yetkiniz yok!", show_alert=True)
        return

    if not ACTIVITY_GROUP_ID:
        await query.answer("❌ Grup tanımlı değil!", show_alert=True)
        return

    success, msg = await remove_excluded_user(ACTIVITY_GROUP_ID, telegram_id)

    if success:
        await query.answer("✅ Kullanıcı listeden çıkarıldı!", show_alert=True)
    else:
        await query.answer(msg, show_alert=True)

    # Menüyü yenile
    await show_tag_excluded_menu(query, user_id, context)


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
        except TelegramError:
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


async def handle_ben_stats(query, user_id: int, target_user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    .ben stats callback - İstatistikleri göster
    Sadece hedef kullanıcı tıklayabilir
    """
    from services.message_service import get_full_user_stats
    from templates import STATS

    # Sadece hedef kullanıcı tıklayabilir
    if user_id != target_user_id:
        await query.answer("Bu buton sana ait değil!", show_alert=True)
        return

    # Grup ID'sini al
    chat = query.message.chat
    if not chat or chat.type not in ['group', 'supergroup']:
        await query.answer("Bu komut sadece gruplarda çalışır.", show_alert=True)
        return

    # İstatistikleri al
    stats = await get_full_user_stats(user_id, chat.id)

    if stats:
        # Kullanıcı bilgilerini al
        try:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.username
            first_name = user_info.first_name or "Kullanıcı"
        except TelegramError:
            username = None
            first_name = "Kullanıcı"

        # İstatistik kartını oluştur
        username_line = f"• @{username}" if username else ""

        if stats.get('randy_participated', 0) > 0:
            win_rate = (stats.get('randy_won', 0) / stats['randy_participated']) * 100
            win_rate_line = f"    Oran  ➜  <b>%{win_rate:.1f}</b>"
        else:
            win_rate_line = ""

        # Kullanıcı mention'ı
        display_name = f"@{username}" if username else first_name
        mention = f'<a href="tg://user?id={user_id}">{display_name}</a>'

        stats_text = STATS["USER_CARD"].format(
            name=first_name,
            username_line=username_line,
            daily=stats.get('daily', 0),
            weekly=stats.get('weekly', 0),
            monthly=stats.get('monthly', 0),
            total=stats.get('total', 0),
            randy_participated=stats.get('randy_participated', 0),
            randy_won=stats.get('randy_won', 0),
            win_rate_line=win_rate_line,
            daily_rank=stats.get('daily_rank', '-'),
            weekly_rank=stats.get('weekly_rank', '-'),
            monthly_rank=stats.get('monthly_rank', '-'),
            activity_rank=stats.get('activity_rank', '-')
        )

        # Mention ekle
        stats_text = f"👋 {mention}\n\n{stats_text}"
    else:
        stats_text = STATS["KAYIT_YOK"]

    # Alert olarak göster
    await query.answer(show_alert=False)

    # Mevcut mesajı düzenle ve istatistikleri göster (buton kalkar)
    try:
        await query.edit_message_text(
            stats_text,
            parse_mode="HTML"
        )
    except TelegramError:
        # Düzenlenemezse yeni mesaj gönder
        await context.bot.send_message(
            chat_id=chat.id,
            text=stats_text,
            parse_mode="HTML"
        )


# ============================================
# RANDY KATILIM
# ============================================

# ============================================
# ÇEKİLİŞ MENÜ FONKSİYONLARI
# ============================================

async def show_cekilis_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş ana menüsünü göster"""
    from config import ACTIVITY_GROUP_ID

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Çekiliş yönetimi için ana gruptaki admin olmanız gerekiyor.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Aktif çekiliş var mı kontrol et
    active_giveaway = None
    if ACTIVITY_GROUP_ID:
        active_giveaway = await get_active_giveaway(ACTIVITY_GROUP_ID)

    keyboard = [
        [InlineKeyboardButton("⚙️ Çekiliş Ayarları", callback_data="cekilis_settings")],
    ]

    if active_giveaway:
        keyboard.append([InlineKeyboardButton("🎯 Aktif Çekiliş", callback_data="cekilis_active")])
        keyboard.append([InlineKeyboardButton("❌ Çekilişi İptal Et", callback_data="cekilis_cancel")])
    else:
        keyboard.append([InlineKeyboardButton("🎁 Yeni Çekiliş Başlat", callback_data="cekilis_create")])

    keyboard.append([InlineKeyboardButton("📜 Geçmiş Çekilişler", callback_data="cekilis_past")])
    keyboard.append([InlineKeyboardButton("🏆 En Çok Kazananlar", callback_data="cekilis_top_winners")])
    keyboard.append([InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")])

    await query.edit_message_text(
        GIVEAWAY["MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_cekilis_settings(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş ayarlarını göster"""
    from config import ACTIVITY_GROUP_ID

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Ayarları getir veya varsayılan değerler kullan
    settings = await get_giveaway_settings(ACTIVITY_GROUP_ID)

    if not settings:
        settings = {
            'default_duration_hours': 2,
            'default_winner_count': 1,
            'max_wins_per_user': 0,
            'pin_announcement': True,
            'pin_winner_message': True,
            'notify_admin_group': True,
            'pin_in_admin_group': True,
            'admin_group_id': None
        }

    duration = settings.get('default_duration_hours', 2)
    winners = settings.get('default_winner_count', 1)
    max_wins = settings.get('max_wins_per_user', 0)
    pin_ann = "✅" if settings.get('pin_announcement', True) else "❌"
    pin_win = "✅" if settings.get('pin_winner_message', True) else "❌"
    notify_admin = "✅" if settings.get('notify_admin_group', True) else "❌"
    pin_admin = "✅" if settings.get('pin_in_admin_group', True) else "❌"

    max_wins_text = f"{max_wins}" if max_wins > 0 else "Sınırsız"

    keyboard = [
        [
            InlineKeyboardButton(f"⏱️ Süre: {duration}s", callback_data="cekilis_duration_menu"),
        ],
        [
            InlineKeyboardButton(f"🏆 Kazanan: {winners}", callback_data="cekilis_winners_menu"),
        ],
        [
            InlineKeyboardButton(f"🔢 Limit: {max_wins_text}", callback_data="cekilis_limit_menu"),
        ],
        [
            InlineKeyboardButton(f"{pin_ann} Duyuru Sabitle", callback_data="cekilis_toggle_pin_ann"),
        ],
        [
            InlineKeyboardButton(f"{pin_win} Kazanan Sabitle", callback_data="cekilis_toggle_pin_win"),
        ],
        [
            InlineKeyboardButton(f"{notify_admin} Yönetime Bildir", callback_data="cekilis_toggle_notify_admin"),
        ],
        [
            InlineKeyboardButton(f"{pin_admin} Yönetimde Sabitle", callback_data="cekilis_toggle_pin_admin"),
        ],
        [InlineKeyboardButton("👥 Yönetim Grubu Ayarla", callback_data="cekilis_set_admin_group")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")],
    ]

    text = GIVEAWAY["SETTINGS_MENU"].format(
        duration=duration,
        winners=winners,
        max_wins=max_wins_text,
        pin_ann=pin_ann,
        pin_win=pin_win,
        notify_admin=notify_admin,
        pin_admin=pin_admin
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_active_cekilis(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktif çekilişi göster"""
    from config import ACTIVITY_GROUP_ID
    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    giveaway = await get_active_giveaway(ACTIVITY_GROUP_ID)

    if not giveaway:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            GIVEAWAY["NO_ACTIVE"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Kazanma zamanlarını getir
    win_times = await get_giveaway_win_times(giveaway['id'])
    win_times_text = format_giveaway_win_times(win_times, show_winners=True)

    # Tarihleri formatla
    started_at = giveaway.get('started_at')
    ends_at = giveaway.get('ends_at')

    if started_at:
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        start_local = started_at.astimezone(TR_TZ)
        start_str = start_local.strftime("%d.%m.%Y %H:%M")
    else:
        start_str = "-"

    if ends_at:
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        end_local = ends_at.astimezone(TR_TZ)
        end_str = end_local.strftime("%d.%m.%Y %H:%M")
    else:
        end_str = "-"

    text = GIVEAWAY["ACTIVE_GIVEAWAY"].format(
        prize=giveaway.get('prize_text', 'Belirtilmedi'),
        duration=giveaway.get('duration_hours', 0),
        winner_count=giveaway.get('winner_count', 1),
        start_time=start_str,
        end_time=end_str,
        win_times=win_times_text
    )

    keyboard = [
        [InlineKeyboardButton("❌ Çekilişi İptal Et", callback_data="cekilis_cancel")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_past_cekilisler(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Geçmiş çekilişleri göster"""
    from config import ACTIVITY_GROUP_ID

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    giveaways = await get_past_giveaways(ACTIVITY_GROUP_ID, limit=10)

    if not giveaways:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            GIVEAWAY["NO_PAST"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    giveaway_list = format_giveaway_list(giveaways)

    keyboard = []
    # Her çekiliş için detay butonu
    for g in giveaways[:5]:  # İlk 5 çekiliş için buton
        giveaway_id = g.get('id')
        prize = g.get('prize_text', 'Ödül')
        if len(prize) > 20:
            prize = prize[:17] + "..."
        keyboard.append([
            InlineKeyboardButton(f"#{giveaway_id} {prize}", callback_data=f"cekilis_detail_{giveaway_id}")
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")])

    text = GIVEAWAY["PAST_GIVEAWAYS"].format(
        giveaway_list=giveaway_list,
        count=len(giveaways)
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_top_winners(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """En çok kazananları göster"""
    from config import ACTIVITY_GROUP_ID

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    winners = await get_top_winners(ACTIVITY_GROUP_ID, limit=10)

    if not winners:
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]
        await query.edit_message_text(
            "🏆 <b>En Çok Kazananlar</b>\n\nHenüz kazanan yok.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    winner_list = format_top_winners(winners)

    text = GIVEAWAY["TOP_WINNERS"].format(winner_list=winner_list)

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def start_cekilis_create(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş oluşturma başlat - ödül metnini iste"""
    context.user_data['waiting_for'] = 'cekilis_prize'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_menu")]]

    await query.edit_message_text(
        GIVEAWAY["CREATE_PROMPT_PRIZE"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cancel_active_cekilis(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktif çekilişi iptal et"""
    from config import ACTIVITY_GROUP_ID
    from services.giveaway_service import stop_giveaway_watcher

    if not ACTIVITY_GROUP_ID:
        await query.answer("❌ Grup tanımlı değil!", show_alert=True)
        return

    giveaway = await get_active_giveaway(ACTIVITY_GROUP_ID)

    if not giveaway:
        await query.answer("❌ Aktif çekiliş yok!", show_alert=True)
        await show_cekilis_menu(query, user_id, context)
        return

    # Çekilişi iptal et
    success = await cancel_giveaway(giveaway['id'])

    if success:
        # Watcher'ı durdur
        stop_giveaway_watcher(giveaway['id'])

        await query.answer("✅ Çekiliş iptal edildi!", show_alert=True)

        # Gruba bildirim gönder
        try:
            await context.bot.send_message(
                ACTIVITY_GROUP_ID,
                "❌ <b>Çekiliş iptal edildi.</b>",
                parse_mode="HTML"
            )
        except TelegramError:
            pass
    else:
        await query.answer("❌ İptal işlemi başarısız!", show_alert=True)

    await show_cekilis_menu(query, user_id, context)


async def show_cekilis_detail(query, user_id: int, giveaway_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş detayını göster"""
    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    giveaway = await get_giveaway_by_id(giveaway_id)

    if not giveaway:
        await query.answer("❌ Çekiliş bulunamadı!", show_alert=True)
        await show_past_cekilisler(query, user_id, context)
        return

    # Kazananları getir
    winners = await get_giveaway_winners(giveaway_id)
    win_times = await get_giveaway_win_times(giveaway_id)

    # Tarihleri formatla
    started_at = giveaway.get('started_at')
    ended_at = giveaway.get('ended_at')

    if started_at:
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        start_local = started_at.astimezone(TR_TZ)
        start_str = start_local.strftime("%d.%m.%Y %H:%M")
    else:
        start_str = "-"

    if ended_at:
        if ended_at.tzinfo is None:
            ended_at = ended_at.replace(tzinfo=timezone.utc)
        end_local = ended_at.astimezone(TR_TZ)
        end_str = end_local.strftime("%d.%m.%Y %H:%M")
    else:
        end_str = "-"

    win_times_text = format_giveaway_win_times(win_times, show_winners=True)

    status = giveaway.get('status', 'ended')
    status_text = "🎊 Tamamlandı" if status == 'ended' else "❌ İptal Edildi"

    text = (
        f"📋 <b>Çekiliş #{giveaway_id} Detayı</b>\n\n"
        f"🎯 <b>Ödül:</b> {giveaway.get('prize_text', '-')}\n"
        f"📊 <b>Durum:</b> {status_text}\n"
        f"⏱️ <b>Süre:</b> {giveaway.get('duration_hours', 0)} saat\n"
        f"🏆 <b>Kazanan Sayısı:</b> {giveaway.get('winner_count', 1)}\n"
        f"📅 <b>Başlangıç:</b> {start_str}\n"
        f"🏁 <b>Bitiş:</b> {end_str}\n\n"
        f"<b>Kazanma Zamanları:</b>\n{win_times_text}"
    )

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_past")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def set_cekilis_duration(query, user_id: int, hours: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş süresini ayarla"""
    from config import ACTIVITY_GROUP_ID

    await update_giveaway_setting(ACTIVITY_GROUP_ID, default_duration_hours=hours)
    await query.answer(f"✅ Süre {hours} saat olarak ayarlandı!", show_alert=True)
    await show_cekilis_settings(query, user_id, context)


async def set_cekilis_winners(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş kazanan sayısını ayarla"""
    from config import ACTIVITY_GROUP_ID

    await update_giveaway_setting(ACTIVITY_GROUP_ID, default_winner_count=count)
    await query.answer(f"✅ Kazanan sayısı {count} olarak ayarlandı!", show_alert=True)
    await show_cekilis_settings(query, user_id, context)


async def set_cekilis_limit(query, user_id: int, limit: int, context: ContextTypes.DEFAULT_TYPE):
    """Kişi başı kazanma limitini ayarla"""
    from config import ACTIVITY_GROUP_ID

    await update_giveaway_setting(ACTIVITY_GROUP_ID, max_wins_per_user=limit)
    limit_text = f"{limit}" if limit > 0 else "Sınırsız"
    await query.answer(f"✅ Limit {limit_text} olarak ayarlandı!", show_alert=True)
    await show_cekilis_settings(query, user_id, context)


async def toggle_cekilis_setting(query, user_id: int, setting_name: str, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş ayarını aç/kapat"""
    from config import ACTIVITY_GROUP_ID

    settings = await get_giveaway_settings(ACTIVITY_GROUP_ID)

    if not settings:
        settings = {}

    current_value = settings.get(setting_name, True)
    new_value = not current_value

    await update_giveaway_setting(ACTIVITY_GROUP_ID, **{setting_name: new_value})

    status = "açıldı" if new_value else "kapatıldı"
    await query.answer(f"✅ Ayar {status}!", show_alert=True)
    await show_cekilis_settings(query, user_id, context)


async def prompt_admin_group(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Yönetim grubu ID'sini iste"""
    context.user_data['waiting_for'] = 'cekilis_admin_group'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_settings")]]

    await query.edit_message_text(
        "👥 <b>Yönetim Grubu</b>\n\n"
        "Kazanan bildirimlerinin gönderileceği yönetim grubunun ID'sini girin.\n\n"
        "<i>Grup ID'sini bulmak için gruba @userinfobot ekleyebilirsiniz.</i>\n\n"
        "Örnek: <code>-1001234567890</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_duration_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekiliş süresi seçim menüsü"""
    keyboard = [
        [
            InlineKeyboardButton("1 Saat", callback_data="cekilis_set_duration_1"),
            InlineKeyboardButton("2 Saat", callback_data="cekilis_set_duration_2"),
        ],
        [
            InlineKeyboardButton("3 Saat", callback_data="cekilis_set_duration_3"),
            InlineKeyboardButton("4 Saat", callback_data="cekilis_set_duration_4"),
        ],
        [
            InlineKeyboardButton("6 Saat", callback_data="cekilis_set_duration_6"),
            InlineKeyboardButton("8 Saat", callback_data="cekilis_set_duration_8"),
        ],
        [
            InlineKeyboardButton("12 Saat", callback_data="cekilis_set_duration_12"),
            InlineKeyboardButton("24 Saat", callback_data="cekilis_set_duration_24"),
        ],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_settings")],
    ]

    await query.edit_message_text(
        "⏱️ <b>Çekiliş Süresi</b>\n\nVarsayılan çekiliş süresini seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_winners_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kazanan sayısı için yazı girişi iste"""
    context.user_data['waiting_for'] = 'cekilis_winner_count'

    keyboard = [
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_settings")],
    ]

    await query.edit_message_text(
        "🏆 <b>Kazanan Sayısı</b>\n\n"
        "Varsayılan kazanan sayısını yazın:\n"
        "<i>(Örn: 1, 5, 10, 50...)</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_limit_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kişi başı kazanma limiti seçim menüsü"""
    keyboard = [
        [
            InlineKeyboardButton("Sınırsız", callback_data="cekilis_set_limit_0"),
        ],
        [
            InlineKeyboardButton("1", callback_data="cekilis_set_limit_1"),
            InlineKeyboardButton("2", callback_data="cekilis_set_limit_2"),
            InlineKeyboardButton("3", callback_data="cekilis_set_limit_3"),
        ],
        [
            InlineKeyboardButton("5", callback_data="cekilis_set_limit_5"),
            InlineKeyboardButton("10", callback_data="cekilis_set_limit_10"),
        ],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="cekilis_settings")],
    ]

    await query.edit_message_text(
        "🔢 <b>Kişi Başı Kazanma Limiti</b>\n\n"
        "Bir kullanıcının maksimum kaç kez kazanabileceğini seçin:\n\n"
        "<i>0 = Sınırsız</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def confirm_start_cekilis(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Çekilişi onaylayıp başlat"""
    from config import ACTIVITY_GROUP_ID
    from templates import GIVEAWAY

    if not ACTIVITY_GROUP_ID:
        await query.answer("❌ Grup tanımlı değil!", show_alert=True)
        return

    # Ödül metnini al
    prize_text = context.user_data.get('cekilis_prize')

    if not prize_text:
        await query.answer("❌ Ödül metni bulunamadı!", show_alert=True)
        await show_cekilis_menu(query, user_id, context)
        return

    # Ayarlardan değerleri al
    settings = await get_giveaway_settings(ACTIVITY_GROUP_ID)

    if settings:
        duration = settings.get('default_duration_hours', 2)
        winner_count = settings.get('default_winner_count', 1)
        max_wins = settings.get('max_wins_per_user', 0)
        pin_announcement = settings.get('pin_announcement', True)
        pin_winner_message = settings.get('pin_winner_message', True)
        notify_admin_group = settings.get('notify_admin_group', True)
        pin_in_admin_group = settings.get('pin_in_admin_group', True)
    else:
        duration = 2
        winner_count = 1
        max_wins = 0
        pin_announcement = True
        pin_winner_message = True
        notify_admin_group = True
        pin_in_admin_group = True

    # Çekiliş oluştur
    success, giveaway_data = await create_giveaway(
        group_id=ACTIVITY_GROUP_ID,
        creator_id=user_id,
        prize_text=prize_text,
        duration_hours=duration,
        winner_count=winner_count,
        max_wins_per_user=max_wins,
        pin_announcement=pin_announcement,
        pin_winner_message=pin_winner_message,
        notify_admin_group=notify_admin_group,
        pin_in_admin_group=pin_in_admin_group
    )

    if not success:
        if giveaway_data and giveaway_data.get("error") == "already_active":
            await query.answer("⚠️ Bu grupta zaten aktif bir çekiliş var!", show_alert=True)
        else:
            await query.answer("❌ Çekiliş oluşturulamadı!", show_alert=True)
        await show_cekilis_menu(query, user_id, context)
        return

    # Watcher başlat
    await start_giveaway_watcher(giveaway_data['id'], ACTIVITY_GROUP_ID, context.bot)

    # Gruba duyuru mesajı gönder
    announcement_text = GIVEAWAY["ANNOUNCEMENT"].format(
        prize=prize_text,
        duration=duration,
        winner_count=winner_count
    )

    try:
        ann_msg = await context.bot.send_message(
            ACTIVITY_GROUP_ID,
            announcement_text,
            parse_mode="HTML"
        )

        # Mesaj ID'sini kaydet
        await update_announcement_message_id(giveaway_data['id'], ann_msg.message_id)

        # Sabitleme
        if pin_announcement:
            try:
                await context.bot.pin_chat_message(
                    ACTIVITY_GROUP_ID,
                    ann_msg.message_id,
                    disable_notification=True
                )
            except TelegramError:
                pass

    except TelegramError as e:
        logger.error(f"❌ Çekiliş duyuru hatası: {e}")

    # Context'i temizle
    context.user_data.pop('cekilis_prize', None)

    await query.answer("✅ Çekiliş başlatıldı!", show_alert=True)

    # Aktif çekiliş menüsünü göster
    await show_active_cekilis(query, user_id, context)


# ============================================
# HAFTALIK ÖDÜL MENÜ FONKSİYONLARI
# ============================================

async def show_weekly_rewards_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Haftalık ödül ayarları menüsünü göster - sadece kişi sayısı ve ödüller"""
    from config import ACTIVITY_GROUP_ID
    from services.weekly_rewards_service import (
        get_weekly_reward_settings, get_rewards_for_group
    )

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Haftalık ödül ayarları için ana gruptaki admin olmanız gerekiyor.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Ayarları getir
    settings = await get_weekly_reward_settings(ACTIVITY_GROUP_ID)
    rewards = await get_rewards_for_group(ACTIVITY_GROUP_ID)

    if settings:
        top_count = settings.get('top_count', 5)
    else:
        top_count = 5

    # Ödül listesi
    rewards_list = format_rewards_list(rewards, top_count)

    keyboard = [
        [InlineKeyboardButton(f"📊 Kişi Sayısı: {top_count}", callback_data="weekly_rewards_top_menu")],
    ]

    # Her sıra için ödül ayarlama butonları
    for i in range(1, top_count + 1):
        reward = next((r['reward_text'] for r in rewards if r['rank'] == i), "—")
        if len(reward) > 20:
            reward = reward[:17] + "..."
        keyboard.append([
            InlineKeyboardButton(f"🎁 {i}. Ödül: {reward}", callback_data=f"weekly_set_reward_{i}")
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")])

    text = (
        "🏆 <b>Haftalık Ödül Ayarları</b>\n\n"
        f"<b>Kaç kişi ödül alacak:</b> {top_count} kişi\n\n"
        f"<b>Ödüller:</b>\n{rewards_list}\n\n"
        "💡 <i>Grupta</i> <code>.haftalık</code> <i>yazarak sıralamayı ve ödülleri görebilirsiniz.</i>"
    )

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except TelegramError:
        # Mesaj içeriği aynıysa hata fırlatılır, bu durumu yoksay
        pass


async def show_weekly_top_count_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kaç kişi ödül alacak seçim menüsü"""
    from config import ACTIVITY_GROUP_ID
    from services.weekly_rewards_service import get_weekly_reward_settings

    settings = await get_weekly_reward_settings(ACTIVITY_GROUP_ID)
    current = settings.get('top_count', 5) if settings else 5

    keyboard = [
        [
            InlineKeyboardButton(f"3{' ✓' if current == 3 else ''}", callback_data="weekly_rewards_top_3"),
            InlineKeyboardButton(f"5{' ✓' if current == 5 else ''}", callback_data="weekly_rewards_top_5"),
            InlineKeyboardButton(f"7{' ✓' if current == 7 else ''}", callback_data="weekly_rewards_top_7"),
        ],
        [
            InlineKeyboardButton(f"10{' ✓' if current == 10 else ''}", callback_data="weekly_rewards_top_10"),
            InlineKeyboardButton(f"15{' ✓' if current == 15 else ''}", callback_data="weekly_rewards_top_15"),
            InlineKeyboardButton(f"20{' ✓' if current == 20 else ''}", callback_data="weekly_rewards_top_20"),
        ],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="weekly_rewards_menu")],
    ]

    await query.edit_message_text(
        "📊 <b>Kaç Kişi Ödül Alacak?</b>\n\n"
        f"Şu anki değer: <b>{current}</b> kişi\n\n"
        "Haftalık en aktif kaç kişinin listeye gireceğini seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def set_weekly_top_count(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Kaç kişi ödül alacağını ayarla"""
    from config import ACTIVITY_GROUP_ID
    from services.weekly_rewards_service import update_top_count

    await update_top_count(ACTIVITY_GROUP_ID, count)
    await query.answer(f"✅ {count} kişi ödül alacak!", show_alert=True)
    await show_weekly_rewards_menu(query, user_id, context)


async def prompt_set_reward(query, user_id: int, rank: int, context: ContextTypes.DEFAULT_TYPE):
    """Ödül tanımlama için yazı iste"""
    context.user_data['waiting_for'] = 'weekly_reward'
    context.user_data['weekly_reward_rank'] = rank

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="weekly_rewards_menu")]]

    await query.edit_message_text(
        WEEKLY_REWARDS["SET_REWARD_PROMPT"].format(rank=rank),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ============================================
# AKTİVİTE MENÜ FONKSİYONLARI
# ============================================

async def show_activity_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktivite ana menüsünü göster - Manuel başlat/durdur sistemi"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import (
        get_activity_settings, get_activity_rewards,
        get_activity_type_text, ACTIVITY_TYPES, ensure_activity_tables,
        get_activity_status
    )
    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    # Tabloların oluşturulduğundan emin ol
    await ensure_activity_tables()

    # Admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Aktivite ayarları için ana gruptaki admin olmanız gerekiyor.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if not ACTIVITY_GROUP_ID:
        keyboard = [[InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")]]
        await query.edit_message_text(
            "❌ ACTIVITY_GROUP_ID tanımlı değil.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Durumu detaylı getir
    status_info = await get_activity_status(ACTIVITY_GROUP_ID)
    settings = await get_activity_settings(ACTIVITY_GROUP_ID)

    activity_type = status_info.get('activity_type', 'weekly')
    enabled = status_info.get('enabled', False)
    top_count = status_info.get('top_count', 20)
    started_at = status_info.get('started_at')
    has_data = status_info.get('has_data', False)

    type_text = get_activity_type_text(activity_type)

    # Durum metni
    if enabled:
        status = "🟢 Aktif - Sayım Devam Ediyor"
        toggle_text = "🔴 Durdur"
    elif has_data:
        status = "🟡 Durdu - Son Sıralama Mevcut"
        toggle_text = "🟢 Yeni Başlat (Sıfırla)"
    else:
        status = "⚪ Başlatılmadı"
        toggle_text = "🟢 Başlat"

    # Başlama tarihi
    if started_at:
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        started_local = started_at.astimezone(TR_TZ)
        started_text = started_local.strftime("%d.%m.%Y %H:%M")
    else:
        started_text = "—"

    # Ödülleri getir
    rewards = await get_activity_rewards(ACTIVITY_GROUP_ID, activity_type)

    keyboard = [
        [InlineKeyboardButton(f"📊 Periyod: {type_text}", callback_data="activity_settings")],
        [InlineKeyboardButton(f"👥 Kişi Sayısı: {top_count}", callback_data="activity_top_menu")],
        [InlineKeyboardButton("🎁 Ödülleri Ayarla", callback_data="activity_rewards_menu")],
        [InlineKeyboardButton(toggle_text, callback_data="activity_toggle")],
        [InlineKeyboardButton(BUTTONS["ANA_MENU"], callback_data="main_menu")],
    ]

    # Ödül listesi
    rewards_text = ""
    if rewards:
        for r in rewards[:5]:
            rewards_text += f"  {r['rank']}. {r['reward_text']}\n"
        if len(rewards) > 5:
            rewards_text += f"  ... ve {len(rewards) - 5} ödül daha\n"
    else:
        rewards_text = "  Henüz ödül tanımlanmamış\n"

    text = (
        "🏆 <b>Aktivite Ödül Sistemi</b>\n\n"
        f"<b>Durum:</b> {status}\n"
        f"<b>Periyod:</b> {type_text}\n"
        f"<b>Başlama:</b> {started_text}\n"
        f"<b>Gösterilecek:</b> {top_count} kişi\n\n"
        f"<b>Ödüller:</b>\n{rewards_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Nasıl Çalışır:</b>\n"
        "• <b>Başlat:</b> Sayaçlar sıfırlanır, yeni sayım başlar\n"
        "• <b>Durdur:</b> Sayım durur, son sıralama kalır\n"
        "• <code>.aktiflik</code> ile grupta sıralamayı görün\n"
        "• <code>.günlük</code> <code>.haftalık</code> <code>.aylık</code> otomatik sıfırlanır"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_activity_settings(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktivite tipi seçim menüsü"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, ACTIVITY_TYPES

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    current = settings.get('activity_type', 'weekly') if settings else 'weekly'

    keyboard = [
        [InlineKeyboardButton(f"📅 Günlük{' ✓' if current == 'daily' else ''}", callback_data="activity_type_daily")],
        [InlineKeyboardButton(f"📆 Haftalık{' ✓' if current == 'weekly' else ''}", callback_data="activity_type_weekly")],
        [InlineKeyboardButton(f"📅 Aylık{' ✓' if current == 'monthly' else ''}", callback_data="activity_type_monthly")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_menu")],
    ]

    await query.edit_message_text(
        "📊 <b>Aktivite Tipi Seçin</b>\n\n"
        "Sıralama hangi periyotta hesaplansın?\n\n"
        f"<b>Şu anki:</b> {ACTIVITY_TYPES.get(current, current)}\n\n"
        "• <b>Günlük:</b> Her gün sıfırlanır\n"
        "• <b>Haftalık:</b> Her Pazartesi sıfırlanır\n"
        "• <b>Aylık:</b> Her ayın 1'inde sıfırlanır",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def set_activity_type(query, user_id: int, activity_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Aktivite tipini ayarla"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import create_or_update_activity_settings, get_activity_type_text

    await create_or_update_activity_settings(ACTIVITY_GROUP_ID, activity_type=activity_type)

    type_text = get_activity_type_text(activity_type)
    await query.answer(f"✅ Aktivite tipi {type_text} olarak ayarlandı!", show_alert=True)

    await show_activity_menu(query, user_id, context)


async def show_activity_top_count_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kaç kişi gösterileceğini seç"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    current = settings.get('top_count', 20) if settings else 20

    keyboard = [
        [
            InlineKeyboardButton(f"10{' ✓' if current == 10 else ''}", callback_data="activity_top_10"),
            InlineKeyboardButton(f"15{' ✓' if current == 15 else ''}", callback_data="activity_top_15"),
            InlineKeyboardButton(f"20{' ✓' if current == 20 else ''}", callback_data="activity_top_20"),
        ],
        [
            InlineKeyboardButton(f"25{' ✓' if current == 25 else ''}", callback_data="activity_top_25"),
            InlineKeyboardButton(f"30{' ✓' if current == 30 else ''}", callback_data="activity_top_30"),
            InlineKeyboardButton(f"50{' ✓' if current == 50 else ''}", callback_data="activity_top_50"),
        ],
        [InlineKeyboardButton("✏️ Manuel Gir", callback_data="activity_top_custom")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_menu")],
    ]

    await query.edit_message_text(
        "👥 <b>Kaç Kişi Gösterilecek?</b>\n\n"
        f"Şu anki değer: <b>{current}</b> kişi\n\n"
        "Sıralamada kaç kişi listelensin?\n\n"
        "💡 <i>Listede olmayan bir sayı için \"Manuel Gir\" butonunu kullanın.</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def prompt_activity_top_custom(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Manuel kişi sayısı girişi için prompt"""
    context.user_data['waiting_for'] = 'activity_top_custom'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_top_menu")]]

    await query.edit_message_text(
        "✏️ <b>Manuel Kişi Sayısı</b>\n\n"
        "Sıralamada gösterilecek kişi sayısını yazın:\n\n"
        "<i>Örnek: 35</i>\n\n"
        "⚠️ <b>Not:</b> 1-100 arası bir sayı giriniz.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def set_activity_top_count(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Kişi sayısını ayarla"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import create_or_update_activity_settings

    await create_or_update_activity_settings(ACTIVITY_GROUP_ID, top_count=count)
    await query.answer(f"✅ {count} kişi gösterilecek!", show_alert=True)

    await show_activity_menu(query, user_id, context)


async def show_activity_rewards_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Ödül ayarlama menüsü"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, get_activity_rewards, get_activity_type_text

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    activity_type = settings.get('activity_type', 'weekly') if settings else 'weekly'
    top_count = settings.get('top_count', 20) if settings else 20

    rewards = await get_activity_rewards(ACTIVITY_GROUP_ID, activity_type)
    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}

    type_text = get_activity_type_text(activity_type)

    keyboard = [
        [InlineKeyboardButton("📝 Tümünü Yaz (Alt Alta)", callback_data="activity_set_all_rewards")],
    ]

    # Her sıra için ödül butonu (max 10 göster)
    display_count = min(top_count, 10)
    for i in range(1, display_count + 1):
        reward = rewards_dict.get(i, "—")
        if len(reward) > 25:
            reward = reward[:22] + "..."
        keyboard.append([
            InlineKeyboardButton(f"🎁 {i}. {reward}", callback_data=f"activity_set_reward_{i}")
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_menu")])

    # Mevcut ödül listesi
    rewards_text = ""
    if rewards:
        for r in rewards:
            rewards_text += f"  {r['rank']}. {r['reward_text']}\n"
    else:
        rewards_text = "  Henüz ödül tanımlanmamış\n"

    text = (
        f"🎁 <b>{type_text} Ödülleri</b>\n\n"
        f"<b>Mevcut Ödüller:</b>\n{rewards_text}\n"
        "💡 <b>Toplu Ödül Girişi:</b>\n"
        "<i>\"Tümünü Yaz\" ile ödülleri alt alta yazabilirsiniz.</i>\n"
        "<i>Her satır bir sıranın ödülü olur.</i>"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def prompt_activity_reward(query, user_id: int, rank: int, context: ContextTypes.DEFAULT_TYPE):
    """Tek ödül için yazı iste"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, get_activity_type_text

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    activity_type = settings.get('activity_type', 'weekly') if settings else 'weekly'
    type_text = get_activity_type_text(activity_type)

    context.user_data['waiting_for'] = 'activity_reward'
    context.user_data['activity_reward_rank'] = rank
    context.user_data['activity_reward_type'] = activity_type

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_rewards_menu")]]

    await query.edit_message_text(
        f"🎁 <b>{rank}. Sıra Ödülü ({type_text})</b>\n\n"
        f"Bu sıra için ödül metnini yazın:\n\n"
        f"<i>Örnek: 50 TL Hediye Çeki</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def prompt_all_activity_rewards(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Tüm ödüller için toplu giriş iste"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, get_activity_type_text

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    activity_type = settings.get('activity_type', 'weekly') if settings else 'weekly'
    type_text = get_activity_type_text(activity_type)

    context.user_data['waiting_for'] = 'activity_all_rewards'
    context.user_data['activity_reward_type'] = activity_type

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="activity_rewards_menu")]]

    await query.edit_message_text(
        f"🎁 <b>{type_text} Ödülleri (Toplu Giriş)</b>\n\n"
        f"Ödülleri <b>alt alta</b> yazın.\n"
        f"Her satır bir sıranın ödülü olacak.\n\n"
        f"<b>Örnek:</b>\n"
        f"<code>100 TL Hediye Çeki\n"
        f"50 TL Hediye Çeki\n"
        f"25 TL Hediye Çeki\n"
        f"VIP Üyelik\n"
        f"Premium Rozet</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_activity_toggle_confirm(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktivite başlatma/durdurma için onay ekranı göster"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, get_activity_status

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    status_info = await get_activity_status(ACTIVITY_GROUP_ID)
    enabled = status_info.get('enabled', False)
    has_data = status_info.get('has_data', False)

    if enabled:
        # Durdurma onayı
        text = (
            "🔴 <b>Aktivite Takibini Durdur</b>\n\n"
            "Aktivite takibini durdurmak istediğinizden emin misiniz?\n\n"
            "• Son sıralama kaydedilecek\n"
            "• <code>.aktiflik</code> ile görüntülenebilir\n"
            "• Veriler silinmeyecek"
        )
    else:
        if has_data:
            # Yeniden başlatma onayı (veriler sıfırlanacak)
            text = (
                "🟢 <b>Aktivite Takibini Yeniden Başlat</b>\n\n"
                "⚠️ <b>DİKKAT:</b> Tüm sayaçlar sıfırlanacak!\n\n"
                "Mevcut sıralama silinip yeni sayım başlayacak.\n"
                "Devam etmek istiyor musunuz?"
            )
        else:
            # İlk kez başlatma
            text = (
                "🟢 <b>Aktivite Takibini Başlat</b>\n\n"
                "Aktivite takibini başlatmak istediğinizden emin misiniz?\n\n"
                "• Kullanıcı mesajları sayılmaya başlayacak\n"
                "• <code>.aktiflik</code> ile sıralama görüntülenebilir"
            )

    keyboard = [
        [
            InlineKeyboardButton("✅ Evet", callback_data="activity_toggle_confirm"),
            InlineKeyboardButton("❌ Hayır", callback_data="activity_toggle_cancel"),
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def toggle_activity(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Aktiviteyi başlat/durdur - Manuel sistem"""
    from config import ACTIVITY_GROUP_ID
    from services.activity_service import get_activity_settings, start_activity_tracking, stop_activity_tracking

    settings = await get_activity_settings(ACTIVITY_GROUP_ID)
    enabled = settings.get('enabled', False) if settings else False
    activity_type = settings.get('activity_type', 'weekly') if settings else 'weekly'

    if enabled:
        # Durdur - veriler kalır
        await stop_activity_tracking(ACTIVITY_GROUP_ID)
        await query.answer(
            "🔴 Aktivite takibi durduruldu!\n\nSon sıralama kaydedildi, .aktiflik ile görüntülenebilir.",
            show_alert=True
        )
    else:
        # Başlat - sayaçlar sıfırlanır, yeni başlangıç
        await start_activity_tracking(ACTIVITY_GROUP_ID, activity_type)
        await query.answer(
            "🟢 Aktivite takibi başlatıldı!\n\nTüm sayaçlar sıfırlandı, yeni sayım başladı.",
            show_alert=True
        )

    await show_activity_menu(query, user_id, context)


# ============================================
# HAFTALIK ÖDÜL MENÜ FONKSİYONLARI (Geriye Uyumluluk)
# ============================================

async def show_weekly_rewards_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Eski haftalık menü - Aktivite menüsüne yönlendir"""
    await show_activity_menu(query, user_id, context)


async def show_weekly_top_count_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Eski kişi sayısı menüsü"""
    await show_activity_top_count_menu(query, user_id, context)


async def set_weekly_top_count(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Eski kişi sayısı ayarı"""
    await set_activity_top_count(query, user_id, count, context)


async def prompt_set_reward(query, user_id: int, rank: int, context: ContextTypes.DEFAULT_TYPE):
    """Eski ödül tanımlama"""
    await prompt_activity_reward(query, user_id, rank, context)


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
                except TelegramError:
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

    elif code == "admin_katilamaz":
        await query.answer(RANDY["ADMIN_KATILAMAZ"], show_alert=True)

    else:
        await query.answer(ERRORS["GENEL"], show_alert=True)

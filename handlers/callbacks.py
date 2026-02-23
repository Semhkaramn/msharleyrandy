"""
🔘 Callback Handler
Buton tıklamalarını yönetir
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from templates import (
    MENU, RANDY, BUTTONS, ERRORS, SUCCESS,
    format_winner_list, get_period_text
)
from services.randy_service import (
    create_draft, get_draft, update_draft, delete_draft,
    get_user_admin_groups, join_randy, get_participant_count,
    get_randy_by_id, end_randy
)
from utils.admin_check import is_group_admin


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana callback handler"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # Ana menü
    if data == "main_menu":
        await show_main_menu(query)

    # Randy menüsü
    elif data == "randy_menu":
        await show_randy_menu(query)

    # Yeni Randy oluştur
    elif data == "randy_create":
        await start_randy_creation(query, user_id, context)

    # Grup seçimi
    elif data.startswith("randy_group_"):
        group_id = int(data.replace("randy_group_", ""))
        await select_group(query, user_id, group_id, context)

    # Mesaj ayarla
    elif data == "randy_message":
        await prompt_message(query, user_id, context)

    # Şart seçimi
    elif data == "randy_requirement":
        await show_requirement_menu(query)

    elif data.startswith("randy_req_"):
        req_type = data.replace("randy_req_", "")
        await select_requirement(query, user_id, req_type, context)

    # Mesaj sayısı
    elif data == "randy_msg_count":
        await prompt_message_count(query, user_id, context)

    # Kazanan sayısı
    elif data == "randy_winners":
        await show_winner_count_menu(query)

    elif data.startswith("randy_win_"):
        count = int(data.replace("randy_win_", ""))
        await select_winner_count(query, user_id, count)

    # Medya seçimi
    elif data == "randy_media":
        await show_media_menu(query)

    elif data.startswith("randy_media_"):
        media_type = data.replace("randy_media_", "")
        await select_media_type(query, user_id, media_type, context)

    # Sabitleme
    elif data == "randy_pin":
        await toggle_pin(query, user_id)

    # Önizleme
    elif data == "randy_preview":
        await show_preview(query, user_id)

    # Kaydet
    elif data == "randy_save":
        await save_draft(query, user_id)

    # İptal
    elif data == "randy_cancel":
        await cancel_creation(query, user_id)

    # Geri
    elif data == "randy_back":
        await go_back(query, user_id, context)

    # Randy'ye katıl
    elif data.startswith("randy_join_"):
        randy_id = int(data.replace("randy_join_", ""))
        await handle_randy_join(query, user_id, randy_id)


async def show_main_menu(query):
    """Ana menüyü göster"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["RANDY_YONETIMI"], callback_data="randy_menu")],
        [InlineKeyboardButton(BUTTONS["ISTATISTIKLER"], callback_data="stats_menu")],
    ]

    await query.edit_message_text(
        MENU["ANA_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_randy_menu(query):
    """Randy menüsünü göster"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["YENI_RANDY"], callback_data="randy_create")],
        [InlineKeyboardButton(BUTTONS["AKTIF_RANDYLER"], callback_data="randy_active")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["RANDY_MENU"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def start_randy_creation(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy oluşturmayı başlat - grup seçimi"""
    # Taslak oluştur
    await create_draft(user_id)

    # Admin olduğu grupları getir
    groups = await get_user_admin_groups(user_id)

    if not groups:
        await query.edit_message_text(
            MENU["GRUP_BULUNAMADI"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_menu")]
            ]),
            parse_mode="HTML"
        )
        return

    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                group['title'] or f"Grup {group['group_id']}",
                callback_data=f"randy_group_{group['group_id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="randy_cancel")])

    await query.edit_message_text(
        MENU["GRUP_SEC"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_group(query, user_id: int, group_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Grup seçildi"""
    await update_draft(user_id, group_id=group_id, current_step='setup')
    await show_setup_menu(query, user_id)


async def show_setup_menu(query, user_id: int):
    """Randy ayar menüsünü göster"""
    draft = await get_draft(user_id)

    if not draft:
        await query.edit_message_text(ERRORS["GENEL"])
        return

    # Durumu göster
    message_status = "✅" if draft.get('message') else "❌"
    req_status = "✅" if draft.get('requirement_type') and draft['requirement_type'] != 'none' else "➖"
    winner_status = f"({draft.get('winner_count', 1)})"
    media_status = "✅" if draft.get('media_file_id') else "➖"
    pin_status = "✅" if draft.get('pin_message') else "❌"

    keyboard = [
        [InlineKeyboardButton(f"{message_status} {BUTTONS['MESAJ_AYARLA']}", callback_data="randy_message")],
        [InlineKeyboardButton(f"{req_status} {BUTTONS['SART_AYARLA']}", callback_data="randy_requirement")],
        [InlineKeyboardButton(f"{BUTTONS['KAZANAN_AYARLA']} {winner_status}", callback_data="randy_winners")],
        [InlineKeyboardButton(f"{media_status} {BUTTONS['MEDYA_EKLE']}", callback_data="randy_media")],
        [InlineKeyboardButton(f"{pin_status} {BUTTONS['SABITLE']}", callback_data="randy_pin")],
        [
            InlineKeyboardButton(BUTTONS["ONIZLE"], callback_data="randy_preview"),
            InlineKeyboardButton(BUTTONS["KAYDET"], callback_data="randy_save")
        ],
        [InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="randy_cancel")],
    ]

    await query.edit_message_text(
        MENU["RANDY_OLUSTUR"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def prompt_message(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj girişi iste"""
    context.user_data['waiting_for'] = 'randy_message'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        MENU["MESAJ_AYARLA"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_requirement_menu(query):
    """Şart seçim menüsü"""
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
        MENU["SART_SEC"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_requirement(query, user_id: int, req_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Şart seçildi"""
    await update_draft(user_id, requirement_type=req_type)

    if req_type == 'none':
        await show_setup_menu(query, user_id)
    else:
        # Mesaj sayısı iste
        context.user_data['waiting_for'] = 'randy_msg_count'
        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

        await query.edit_message_text(
            MENU["MESAJ_SAYISI_GIR"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def prompt_message_count(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj sayısı iste"""
    context.user_data['waiting_for'] = 'randy_msg_count'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        MENU["MESAJ_SAYISI_GIR"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_winner_count_menu(query):
    """Kazanan sayısı menüsü"""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="randy_win_1"),
            InlineKeyboardButton("2", callback_data="randy_win_2"),
            InlineKeyboardButton("3", callback_data="randy_win_3"),
        ],
        [
            InlineKeyboardButton("5", callback_data="randy_win_5"),
            InlineKeyboardButton("10", callback_data="randy_win_10"),
            InlineKeyboardButton("15", callback_data="randy_win_15"),
        ],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        MENU["KAZANAN_SAYISI"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_winner_count(query, user_id: int, count: int):
    """Kazanan sayısı seçildi"""
    await update_draft(user_id, winner_count=count)
    await show_setup_menu(query, user_id)


async def show_media_menu(query):
    """Medya seçim menüsü"""
    keyboard = [
        [InlineKeyboardButton(BUTTONS["SADECE_METIN"], callback_data="randy_media_none")],
        [InlineKeyboardButton(BUTTONS["FOTOGRAF"], callback_data="randy_media_photo")],
        [InlineKeyboardButton(BUTTONS["VIDEO"], callback_data="randy_media_video")],
        [InlineKeyboardButton(BUTTONS["GIF"], callback_data="randy_media_animation")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        MENU["MEDYA_SEC"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_media_type(query, user_id: int, media_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Medya tipi seçildi"""
    if media_type == 'none':
        await update_draft(user_id, media_type='none', media_file_id=None)
        await show_setup_menu(query, user_id)
    else:
        await update_draft(user_id, media_type=media_type)
        context.user_data['waiting_for'] = f'randy_media_{media_type}'

        keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

        await query.edit_message_text(
            MENU["MEDYA_GONDER"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def toggle_pin(query, user_id: int):
    """Sabitleme toggle"""
    draft = await get_draft(user_id)

    if draft:
        new_value = not draft.get('pin_message', False)
        await update_draft(user_id, pin_message=new_value)

    await show_setup_menu(query, user_id)


async def show_preview(query, user_id: int):
    """Önizleme göster"""
    draft = await get_draft(user_id)

    if not draft:
        await query.edit_message_text(ERRORS["GENEL"])
        return

    title = draft.get('title', 'Başlık belirlenmedi')
    message = draft.get('message', 'Mesaj belirlenmedi')

    preview = f"🎰 <b>{title}</b>\n\n{message}"

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
    media_names = {'none': 'Yok', 'photo': 'Fotoğraf', 'video': 'Video', 'animation': 'GIF'}
    media = media_names.get(media_type, 'Yok')

    # Pin bilgisi
    pin = "Evet" if draft.get('pin_message') else "Hayır"

    text = MENU["ONIZLEME"].format(
        preview=preview,
        group=f"Grup ID: {draft.get('group_id', 'Belirlenmedi')}",
        requirement=requirement,
        winners=draft.get('winner_count', 1),
        media=media,
        pin=pin
    )

    keyboard = [
        [InlineKeyboardButton(BUTTONS["KAYDET"], callback_data="randy_save")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def save_draft(query, user_id: int):
    """Taslağı kaydet"""
    draft = await get_draft(user_id)

    if not draft:
        await query.edit_message_text(ERRORS["GENEL"])
        return

    # Zorunlu alanları kontrol et
    if not draft.get('group_id'):
        await query.answer("❌ Grup seçilmedi!", show_alert=True)
        return

    if not draft.get('title') or not draft.get('message'):
        await query.answer("❌ Başlık ve mesaj zorunludur!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="main_menu")],
    ]

    await query.edit_message_text(
        MENU["RANDY_KAYDEDILDI"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cancel_creation(query, user_id: int):
    """Oluşturmayı iptal et"""
    await delete_draft(user_id)
    await show_randy_menu(query)


async def go_back(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Geri dön"""
    context.user_data.pop('waiting_for', None)

    draft = await get_draft(user_id)

    if draft and draft.get('group_id'):
        await show_setup_menu(query, user_id)
    else:
        await show_randy_menu(query)


async def handle_randy_join(query, user_id: int, randy_id: int):
    """Randy'ye katılım"""
    username = query.from_user.username
    first_name = query.from_user.first_name

    success, code = await join_randy(randy_id, user_id, username, first_name)

    if success:
        await query.answer(RANDY["BASARIYLA_KATILDIN"], show_alert=True)

        # Katılımcı sayısını güncelle
        count = await get_participant_count(randy_id)
        randy = await get_randy_by_id(randy_id)

        if randy:
            # Mesajı güncelle
            new_text = RANDY["BASLADI"].format(
                title=randy['title'],
                message=randy['message'],
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

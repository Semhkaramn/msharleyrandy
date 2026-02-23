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
    get_randy_by_id, end_randy,
    add_channel_to_draft, remove_channel_from_draft,
    get_draft_channels, clear_draft_channels,
    get_or_create_group_draft
)
from utils.admin_check import is_group_admin, is_activity_group_admin


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana callback handler"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # Menü mesaj ID'sini kaydet (hep aynı mesajı düzenlemek için)
    if query.message:
        context.user_data['menu_message_id'] = query.message.message_id

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
        await show_winner_count_menu(query, context)

    elif data.startswith("randy_win_"):
        count = int(data.replace("randy_win_", ""))
        await select_winner_count(query, user_id, count, context)

    # Medya seçimi
    elif data == "randy_media":
        await show_media_menu(query, context)

    elif data.startswith("randy_media_"):
        media_type = data.replace("randy_media_", "")
        await select_media_type(query, user_id, media_type, context)

    # Kanal ekleme
    elif data == "randy_channels":
        await show_channels_menu(query, user_id, context)

    # Kanal temizle
    elif data == "randy_channels_clear":
        await clear_channels(query, user_id, context)

    # Kanal sil (tek tek)
    elif data.startswith("randy_channel_remove_"):
        channel_id = int(data.replace("randy_channel_remove_", ""))
        await remove_channel(query, user_id, channel_id, context)

    # Sabitleme
    elif data == "randy_pin":
        await toggle_pin(query, user_id, context)

    # Önizleme
    elif data == "randy_preview":
        await show_preview(query, user_id, context)

    # Kaydet
    elif data == "randy_save":
        await save_draft(query, user_id, context)

    # İptal
    elif data == "randy_cancel":
        await cancel_creation(query, user_id, context)

    # Geri
    elif data == "randy_back":
        await go_back(query, user_id, context)

    # Randy'ye katıl
    elif data.startswith("randy_join_"):
        randy_id = int(data.replace("randy_join_", ""))
        await handle_randy_join(query, user_id, randy_id, context)


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
    """Randy oluşturmayı başlat - önce activity group admin kontrolü"""
    from config import ACTIVITY_GROUP_ID

    # Activity group admin kontrolü
    is_admin = await is_activity_group_admin(context.bot, user_id)

    if not is_admin:
        await query.edit_message_text(
            "❌ <b>Yetkiniz Yok</b>\n\n"
            "Randy oluşturmak için ana gruptaki admin olmanız gerekiyor.\n\n"
            "💡 <i>Bot'u gruba ekleyip admin yaptıktan sonra grupta /start komutunu kullanın.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_menu")]
            ]),
            parse_mode="HTML"
        )
        return

    # Taslak oluştur
    await create_draft(user_id)

    # Admin olduğu grupları getir (bot instance'ı ile)
    groups = await get_user_admin_groups(user_id, context.bot)

    # ACTIVITY_GROUP_ID tanımlı ama gruplar boşsa, grubu kaydet
    if not groups and ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
        try:
            # Grup bilgisini Telegram'dan al
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
        await query.edit_message_text(
            "❌ <b>Admin olduğunuz grup bulunamadı.</b>\n\n"
            "Bu sorunu çözmek için:\n"
            "1️⃣ Bot'u gruba ekleyin\n"
            "2️⃣ Bot'a admin yetkisi verin\n"
            "3️⃣ Grupta /start komutunu kullanın\n\n"
            "💡 <i>Bu işlemler bot'un sizi grup admini olarak tanımasını sağlar.</i>",
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
    """Grup seçildi - mevcut grup taslağını kontrol et"""

    # Grup için mevcut taslak varsa onu kullan, yoksa yeni oluştur
    draft = await get_or_create_group_draft(user_id, group_id)

    if not draft:
        await query.edit_message_text(
            "❌ Taslak oluşturulamadı. Lütfen tekrar deneyin.",
            parse_mode="HTML"
        )
        return

    # Context'e aktif grup ID'sini kaydet
    context.user_data['active_group_id'] = group_id

    await show_setup_menu(query, user_id, group_id)


async def show_setup_menu(query, user_id: int, group_id: int = None):
    """Randy ayar menüsünü göster (grup bazlı)"""
    draft = await get_draft(user_id, group_id)

    if not draft:
        await query.edit_message_text(ERRORS["GENEL"])
        return

    # Aktif grup ID'sini güncelle
    group_id = draft.get('group_id')

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

    media_status = "✅" if draft.get('media_file_id') else "➖"
    pin_status = "✅" if draft.get('pin_message') else "❌"
    channel_status = f"✅ ({len(channels)})" if channels else "➖"

    # Oluşturanı göster
    creator_info = ""
    if draft.get('creator_id') and draft['creator_id'] != user_id:
        creator_info = "\n\n<i>📝 Bu taslak başka bir admin tarafından oluşturuldu.</i>"

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
        [InlineKeyboardButton(BUTTONS["IPTAL"], callback_data="randy_cancel")],
    ]

    await query.edit_message_text(
        MENU["RANDY_OLUSTUR"] + creator_info,
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
    group_id = context.user_data.get('active_group_id') if context else None
    await update_draft(user_id, group_id=group_id, requirement_type=req_type)

    if req_type == 'none':
        await show_setup_menu(query, user_id, group_id)
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


async def show_winner_count_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Kazanan sayısı - yazıyla giriş"""
    context.user_data['waiting_for'] = 'randy_winner_count'

    keyboard = [[InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")]]

    await query.edit_message_text(
        "🏆 <b>Kazanan Sayısı</b>\n\n"
        "Kaç kişi kazanacak? Sayı yazın:\n\n"
        "<i>Örnek: 3</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_media_menu(query, context: ContextTypes.DEFAULT_TYPE = None):
    """Medya menüsü - direkt medya iste, seçenek yok"""
    if context:
        context.user_data['waiting_for'] = 'randy_media'

    keyboard = [
        [InlineKeyboardButton("🗑️ Medyayı Kaldır", callback_data="randy_media_none")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        "🖼️ <b>Medya Ekle</b>\n\n"
        "Fotoğraf, video veya GIF gönderin.\n\n"
        "<i>Medya eklemek istemiyorsanız 'Geri' butonuna tıklayın.</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def select_media_type(query, user_id: int, media_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Medya tipi seçildi - sadece none için kullanılır"""
    group_id = context.user_data.get('active_group_id') if context else None

    if media_type == 'none':
        await update_draft(user_id, group_id=group_id, media_type='none', media_file_id=None)
        await query.answer("✅ Medya kaldırıldı!", show_alert=True)
        await show_setup_menu(query, user_id, group_id)
    else:
        # Artık bu duruma düşmemeli ama yine de handle edelim
        await show_media_menu(query, context)


async def select_winner_count(query, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
    """Kazanan sayısı seçildi"""
    group_id = context.user_data.get('active_group_id') if context else None
    await update_draft(user_id, group_id=group_id, winner_count=count)
    await show_setup_menu(query, user_id, group_id)


async def show_channels_menu(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Kanal ekleme menüsü"""
    group_id = context.user_data.get('active_group_id') if context else None
    draft = await get_draft(user_id, group_id)

    if not draft:
        await query.edit_message_text(ERRORS["GENEL"])
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
    group_id = context.user_data.get('active_group_id') if context else None
    await clear_draft_channels(user_id, group_id)
    await query.answer("✅ Tüm kanallar temizlendi!", show_alert=True)
    await show_channels_menu(query, user_id, context)


async def remove_channel(query, user_id: int, channel_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Tek kanal sil"""
    group_id = context.user_data.get('active_group_id') if context else None
    await remove_channel_from_draft(user_id, channel_id, group_id)
    await query.answer("✅ Kanal silindi!", show_alert=True)
    await show_channels_menu(query, user_id, context)


async def toggle_pin(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Sabitleme toggle"""
    group_id = context.user_data.get('active_group_id') if context else None
    draft = await get_draft(user_id, group_id)

    if draft:
        new_value = not draft.get('pin_message', False)
        await update_draft(user_id, group_id=group_id, pin_message=new_value)

    await show_setup_menu(query, user_id, group_id)


async def show_preview(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Önizleme göster"""
    group_id = context.user_data.get('active_group_id') if context else None
    draft = await get_draft(user_id, group_id)

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
        [InlineKeyboardButton(BUTTONS["KAYDET"], callback_data="randy_save")],
        [InlineKeyboardButton(BUTTONS["GERI"], callback_data="randy_back")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def save_draft(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Taslağı kaydet"""
    group_id = context.user_data.get('active_group_id') if context else None
    draft = await get_draft(user_id, group_id)

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


async def cancel_creation(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Oluşturmayı iptal et"""
    group_id = context.user_data.get('active_group_id') if context else None
    await delete_draft(user_id, group_id)
    # Context'i temizle
    if context:
        context.user_data.pop('active_group_id', None)
        context.user_data.pop('waiting_for', None)
    await show_randy_menu(query)


async def go_back(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Geri dön"""
    context.user_data.pop('waiting_for', None)

    # Aktif grup ID'sini context'ten al
    group_id = context.user_data.get('active_group_id')

    draft = await get_draft(user_id, group_id)

    if draft and draft.get('group_id'):
        await show_setup_menu(query, user_id, draft.get('group_id'))
    else:
        await show_randy_menu(query)


async def handle_randy_join(query, user_id: int, randy_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Randy'ye katılım"""
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
            # Şart varsa şartlı template kullan
            req_type = randy.get('requirement_type', 'none')
            req_count = randy.get('required_message_count', 0)

            if req_type != 'none' and req_count > 0:
                period_text = get_period_text(req_type)
                requirement = f"{period_text} {req_count} mesaj"
                new_text = RANDY["BASLADI_SARTLI"].format(
                    title=randy['title'],
                    message=randy['message'],
                    requirement=requirement,
                    participants=count,
                    winners=randy['winner_count']
                )
            else:
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

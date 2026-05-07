"""
🤖 Randy & Roll Telegram Bot
Ana giriş noktası - Heroku'da çalışır

Komutlar:
- /start - Bot başlat (özel)
- /randy - Randy ayarları (özel/grup)
- .ben, !ben, /ben - İstatistikler (grup)
- .inf, /inf - Kullanıcı bilgisi (admin - reply veya @username ile)
- .günlük, .haftalık, .aylık, .aktiflik - Sıralamalar (grup - admin)
- roll X - Roll başlat (grup - admin)
- liste - Roll listesi (grup - admin)
- /etiket [mesaj] - 5'erli toplu etiketleme (grup - admin)
- /naber - Tek tek rastgele mesajlarla etiketleme (grup - admin)
- /dur - Aktif etiketlemeyi durdur (grup - admin)
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN
from database import db
from handlers.commands import (
    start_command,
    randy_command,
    ben_command,
    bilgi_command,
    number_command,
    gunluk_command,
    haftalik_command,
    aylik_command,
    aktiflik_command,
    bitir_command,
    etiket_command,
    naber_command,
    dur_command
)
from handlers.messages import handle_message, handle_member_update
from handlers.callbacks import handle_callback

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Gereksiz logları kapat
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)


async def post_init(application: Application) -> None:
    """Bot başladığında veritabanı bağlantısını kur ve otomatik görevleri başlat"""
    await db.connect()

    # Otomatik etiket görevlerini yeniden başlat
    await _restart_auto_tagging_tasks(application.bot)

    # Aktif çekilişleri yeniden başlat
    await _restart_active_giveaways(application.bot)

    # Aktif Randy mesajlarını güncelle (link preview kapat)
    await _refresh_active_randy_messages(application.bot)

    logger.info("✅ Bot başlatıldı!")


async def _restart_active_giveaways(bot):
    """Bot restart olduğunda aktif çekilişleri yeniden başlat"""
    from services.giveaway_service import restart_active_giveaways

    try:
        await restart_active_giveaways(bot)
        logger.info("🎁 Aktif çekilişler yeniden başlatıldı")
    except Exception as e:
        logger.error(f"❌ Çekiliş yeniden başlatma hatası: {e}")


async def _restart_auto_tagging_tasks(bot):
    """Bot restart olduğunda aktif otomatik etiket görevlerini yeniden başlat"""
    from services.tagging_service import get_auto_tag_settings, start_auto_tagging
    from config import ACTIVITY_GROUP_ID

    try:
        if ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
            settings = await get_auto_tag_settings(ACTIVITY_GROUP_ID)

            if settings and settings.get('enabled'):
                interval = settings.get('interval_minutes', 60)
                await start_auto_tagging(ACTIVITY_GROUP_ID, bot, interval)
                logger.info(f"🤖 Otomatik etiket görevi yeniden başlatıldı (Aralık: {interval} dk)")
    except Exception as e:
        logger.error(f"❌ Otomatik etiket yeniden başlatma hatası: {e}")


async def _refresh_active_randy_messages(bot):
    """Bot restart olduğunda aktif Randy mesajlarını güncelle (link preview kapat)"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
    from telegram.error import TelegramError
    from services.randy_service import get_randy_channels, get_participant_count
    from templates import RANDY as RANDY_TEMPLATES, get_period_text
    from config import ACTIVITY_GROUP_ID

    DISABLE_PREVIEW = LinkPreviewOptions(is_disabled=True)

    try:
        async with db.pool.acquire() as conn:
            # Tüm aktif Randy'leri getir
            active_randys = await conn.fetch("""
                SELECT * FROM randy WHERE status = 'active'
            """)

        if not active_randys:
            return

        for randy in active_randys:
            randy = dict(randy)
            randy_id = randy['id']
            group_id = randy['group_id']
            message_id = randy.get('message_id')

            if not message_id:
                continue

            try:
                # Katılımcı sayısını al
                count = await get_participant_count(randy_id)

                # Zorunlu kanalları al
                channels_list = []

                # Activity group'u ekle
                if ACTIVITY_GROUP_ID and ACTIVITY_GROUP_ID != 0:
                    try:
                        activity_chat = await bot.get_chat(ACTIVITY_GROUP_ID)
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
                    new_text = RANDY_TEMPLATES["BASLADI_SARTLI"].format(
                        message=randy['message'],
                        requirement=requirement,
                        channels_text=channels_text,
                        participants=count,
                        winners=randy['winner_count']
                    )
                else:
                    new_text = RANDY_TEMPLATES["BASLADI"].format(
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

                # Mesajı güncelle
                if randy.get('media_file_id') and randy.get('media_type') != 'none':
                    await bot.edit_message_caption(
                        chat_id=group_id,
                        message_id=message_id,
                        caption=new_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                else:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=message_id,
                        text=new_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML",
                        link_preview_options=DISABLE_PREVIEW
                    )

                logger.info(f"🎲 Randy mesajı güncellendi - Randy ID: {randy_id}, Grup: {group_id}")

            except TelegramError as e:
                logger.warning(f"⚠️ Randy mesajı güncellenemedi - Randy ID: {randy_id}, Hata: {e}")
            except Exception as e:
                logger.error(f"❌ Randy güncelleme hatası - Randy ID: {randy_id}, Hata: {e}")

        logger.info(f"🎲 {len(active_randys)} aktif Randy mesajı kontrol edildi")

    except Exception as e:
        logger.error(f"❌ Randy mesajları güncelleme hatası: {e}")


async def post_shutdown(application: Application) -> None:
    """Bot kapanırken veritabanı bağlantısını kapat"""
    await db.close()
    logger.info("🔌 Bot kapatıldı")


def main():
    """Bot'u başlat"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN bulunamadı! .env dosyasını kontrol edin.")
        return

    # Application oluştur
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ========== KOMUT HANDLER'LARI ==========

    # /start - Özel mesajda bot başlatma
    application.add_handler(CommandHandler("start", start_command))

    # /randy - Özel mesajda Randy ayarları
    application.add_handler(CommandHandler("randy", randy_command))

    # /number X - Kazanan sayısı ayarla (grup)
    application.add_handler(CommandHandler("number", number_command))

    # /bitir - Randy'yi bitir (grup - admin)
    application.add_handler(CommandHandler("bitir", bitir_command))

    # /etiket - Toplu etiketleme (grup - admin)
    application.add_handler(CommandHandler("etiket", etiket_command))

    # /naber - Tek tek rastgele mesajlarla etiketleme (grup - admin)
    application.add_handler(CommandHandler("naber", naber_command))

    # /dur - Etiketlemeyi durdur (grup - admin)
    application.add_handler(CommandHandler("dur", dur_command))

    # .ben, !ben, /ben - Kullanıcı istatistikleri
    application.add_handler(CommandHandler("ben", ben_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'^[.!]ben$') & filters.ChatType.GROUPS,
        ben_command
    ))

    # .inf, /inf - Kullanıcı bilgisi (reply veya @username ile)
    application.add_handler(CommandHandler("inf", bilgi_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'^[.!]inf(\s+@?\w+)?$') & filters.ChatType.GROUPS,
        bilgi_command
    ))

    # .günlük - Günlük sıralama (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]g[üu]nl[üu]k$') & filters.ChatType.GROUPS,
        gunluk_command
    ))

    # .haftalık - Haftalık sıralama (admin) - ödülleri de gösterir
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]haftal[ıi]k$') & filters.ChatType.GROUPS,
        haftalik_command
    ))

    # .aylık - Aylık sıralama (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]ayl[ıi]k$') & filters.ChatType.GROUPS,
        aylik_command
    ))

    # .aktiflik - Aktivite sıralaması (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]aktiflik$') & filters.ChatType.GROUPS,
        aktiflik_command
    ))

    # ========== CALLBACK HANDLER ==========
    application.add_handler(CallbackQueryHandler(handle_callback))

    # ========== ÜYE AYRILMA/BANLANMA HANDLER ==========
    # Kullanıcı gruptan ayrıldığında veya banlandığında veritabanından silinir
    application.add_handler(ChatMemberHandler(
        handle_member_update,
        ChatMemberHandler.CHAT_MEMBER
    ))

    # ========== MESAJ HANDLER ==========
    # Roll komutları + Mesaj sayma (grup) + Randy ayarları (özel)
    # Tüm mesaj tiplerini yakala (TEXT, PHOTO, VIDEO, STICKER vs.)
    # Randy reply bitirme ve medya ekleme için gerekli
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION |
         filters.Sticker.ALL | filters.Document.ALL) & ~filters.COMMAND,
        handle_message
    ))

    # Bot'u çalıştır (polling mode - Heroku için)
    logger.info("🚀 Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

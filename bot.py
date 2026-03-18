"""
🤖 Randy & Roll Telegram Bot
Ana giriş noktası - Heroku'da çalışır

Komutlar:
- /start - Bot başlat (özel)
- /randy - Randy ayarları (özel/grup)
- .ben, !ben, /ben - İstatistikler (grup)
- .bilgi, /bilgi - Kullanıcı bilgisi (admin - reply veya @username ile)
- .günlük, .haftalık, .aylık - Sıralamalar (grup - admin)
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
    bitir_command,
    etiket_command,
    naber_command,
    dur_command
)
from handlers.messages import handle_message
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

    # .bilgi, /bilgi - Kullanıcı bilgisi (reply veya @username ile)
    application.add_handler(CommandHandler("bilgi", bilgi_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'^[.!]bilgi(\s+@?\w+)?$') & filters.ChatType.GROUPS,
        bilgi_command
    ))

    # .günlük - Günlük sıralama (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]g[üu]nl[üu]k$') & filters.ChatType.GROUPS,
        gunluk_command
    ))

    # .haftalık - Haftalık sıralama (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]haftal[ıi]k$') & filters.ChatType.GROUPS,
        haftalik_command
    ))

    # .aylık - Aylık sıralama (admin)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[./!]ayl[ıi]k$') & filters.ChatType.GROUPS,
        aylik_command
    ))

    # ========== CALLBACK HANDLER ==========
    application.add_handler(CallbackQueryHandler(handle_callback))

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

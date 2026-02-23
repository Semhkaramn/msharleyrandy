"""
🤖 Randy & Roll Telegram Bot
Ana giriş noktası - Heroku'da çalışır

Komutlar:
- /start - Bot başlat (özel)
- /randy - Randy ayarları (özel)
- .ben, !ben, /ben - İstatistikler (grup)
- .günlük, .haftalık, .aylık - Sıralamalar (grup - admin)
- roll X - Roll başlat (grup - admin)
- liste - Roll listesi (grup - admin)
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
    number_command,
    gunluk_command,
    haftalik_command,
    aylik_command
)
from handlers.messages import handle_message
from handlers.callbacks import handle_callback

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Bot başladığında veritabanı bağlantısını kur"""
    await db.connect()
    logger.info("✅ Bot başlatıldı!")


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

    # .ben, !ben, /ben - Kullanıcı istatistikleri
    application.add_handler(CommandHandler("ben", ben_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'^[.!]ben$') & filters.ChatType.GROUPS,
        ben_command
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
    # Roll komutları + Mesaj sayma
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_message
    ))

    # Bot'u çalıştır (polling mode - Heroku için)
    logger.info("🚀 Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

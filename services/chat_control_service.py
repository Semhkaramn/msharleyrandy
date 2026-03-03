"""
🌙 Chat Kontrol Servisi
İyi geceler/Günaydın Harley komutları için grup izin yönetimi
"""

from telegram import ChatPermissions
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging

logger = logging.getLogger(__name__)


# İyi geceler - Chat kapalı izinleri (sadece üye ekleme açık)
NIGHT_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,  # sticker, gif vs.
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=True,  # Sadece üye ekleme açık
    can_pin_messages=False,
    can_manage_topics=False,
)

# Günaydın - Sadece metin, sticker, gif ve üye ekleme açık
MORNING_PERMISSIONS = ChatPermissions(
    can_send_messages=True,         # Metin mesajı açık
    can_send_audios=False,          # Ses kapalı
    can_send_documents=False,       # Belge kapalı
    can_send_photos=False,          # Fotoğraf kapalı
    can_send_videos=False,          # Video kapalı
    can_send_video_notes=False,     # Video notu kapalı
    can_send_voice_notes=False,     # Sesli mesaj kapalı
    can_send_polls=False,           # Anket kapalı
    can_send_other_messages=True,   # Sticker, GIF açık
    can_add_web_page_previews=False, # Link önizleme kapalı
    can_change_info=False,
    can_invite_users=True,          # Üye ekleme açık
    can_pin_messages=False,
    can_manage_topics=False,
)


async def close_chat(bot, chat_id: int) -> tuple[bool, str]:
    """
    Chat'i kapat - İyi geceler modu
    Sadece üye ekleme açık kalır, diğer tüm izinler kapatılır
    """
    try:
        await bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=NIGHT_PERMISSIONS,
            use_independent_chat_permissions=True  # İzinleri bağımsız olarak ayarla
        )
        logger.info(f"🌙 Chat kapatıldı: {chat_id}")
        return True, "İyi geceler Harley ailesi 🌙\nChat kapalı"
    except TelegramError as e:
        logger.error(f"❌ Chat kapatma hatası: {e}")
        return False, f"❌ Chat kapatılamadı: {e}"


async def open_chat(bot, chat_id: int) -> tuple[bool, str]:
    """
    Chat'i aç - Günaydın modu
    Mesaj gönderme, gif, sticker ve üye ekleme açılır
    """
    try:
        await bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=MORNING_PERMISSIONS,
            use_independent_chat_permissions=True  # İzinleri bağımsız olarak ayarla
        )
        logger.info(f"☀️ Chat açıldı: {chat_id}")
        return True, "Günaydın Harley ailesi ☀️\nChat aktif"
    except TelegramError as e:
        logger.error(f"❌ Chat açma hatası: {e}")
        return False, f"❌ Chat açılamadı: {e}"

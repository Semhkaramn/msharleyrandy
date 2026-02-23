"""
⚙️ Bot Konfigürasyonu
Environment variables ve sabit ayarlar
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ========== TELEGRAM BOT ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# ========== DATABASE ==========
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ========== CACHE AYARLARI ==========
ADMIN_CACHE_TTL = 300  # 5 dakika (saniye)
CLEANUP_THROTTLE_MS = 30000  # 30 saniye (milisaniye)

# ========== MESAJ SAYMA ==========
# Bu ID'lerden gelen mesajlar sayılmaz
IGNORED_USER_IDS = [
    777000,      # Telegram servis hesabı (bağlı kanallar)
    1087968824,  # GroupAnonymousBot (anonim adminler)
]

# ========== ROLL VARSAYILANLARI ==========
DEFAULT_ROLL_DURATION = 2  # dakika

# ========== RANDY VARSAYILANLARI ==========
DEFAULT_WINNER_COUNT = 1

# ========== MESAJ ŞARTI TİPLERİ ==========
REQUIREMENT_TYPES = {
    "none": "Şartsız",
    "daily": "Günlük Mesaj",
    "weekly": "Haftalık Mesaj",
    "monthly": "Aylık Mesaj",
    "all_time": "Toplam Mesaj",
    "post_randy": "Randy Sonrası Mesaj"
}

# ========== MEDYA TİPLERİ ==========
MEDIA_TYPES = {
    "none": "Sadece Metin",
    "photo": "Fotoğraf",
    "video": "Video",
    "animation": "GIF/Animasyon"
}

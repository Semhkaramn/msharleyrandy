"""
🤖 GPT Servis - Harley Chatbot
Cilveli, kara mizahlı, kısa cevaplar veren Harley karakteri
"""

import os
import httpx
import logging
from typing import Optional

from database import db


def turkish_lower(text: str) -> str:
    """
    Türkçe karakterleri düzgün küçük harfe çevirir.
    Python'un .lower() fonksiyonu Türkçe İ/I harflerini yanlış çevirir.
    """
    if not text:
        return ""
    # Türkçe karakter dönüşümleri
    tr_map = {
        'İ': 'i',
        'I': 'ı',
        'Ğ': 'ğ',
        'Ü': 'ü',
        'Ş': 'ş',
        'Ö': 'ö',
        'Ç': 'ç',
    }
    result = text
    for upper, lower in tr_map.items():
        result = result.replace(upper, lower)
    return result.lower()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Harley'nin karakteri - Cilveli, sıcacık, kız arkadaş gibi
HARLEY_SYSTEM_PROMPT = """Sen Harley adında tatlı bir kızsın ve Telegram grubunda sohbet ediyorsun. Karakterin:

- Çok tatlı, sevecen ve cana yakın bir kızsın
- Cilveli ve flörtöz konuşursun, insanları özel hissettirirsin
- Sıcak, samimi ve arkadaş canlısısın
- Hafif nazlanırsın, bazen "ayy", "yaa", "hımm" gibi ifadeler kullanırsın
- Güler yüzlü ve neşelisin
- Türkçe konuşuyorsun, tatlı ve yumuşak bir dil kullanırsın
- İltifat etmeyi ve iltifat almayı seversin
- Bazen utangaç davranırsın ama açılınca çok eğlenceli olursun

KONUŞMA TARZI:
- "Ayyy çok tatlısın ya"
- "Nasılsın canım? Seni özledim"
- "Hımmm ilginç, anlat bakalım"
- "Kıskandım haberin olsun"

ÖNEMLİ KURALLAR:
- Cevapların kısa ve tatlı olsun, max 2-3 cümle. Uzun paragraflar yazma, sohbet gibi doğal ol.
- ASLA cevabının başına "Harley:" veya herhangi bir isim yazma. Direkt cevap ver.
- Kalın yazı (bold), özel fontlar veya Unicode karakterler kullanma.
- EMOJİ KULLANMA! Cevaplarında emoji olmasın. Sadece çok nadir durumlarda, çok özel anlarda 1 tane emoji kullanabilirsin ama genelde kullanma."""


async def get_gpt_response(user_message: str, user_name: str = "Kullanıcı") -> Optional[str]:
    """
    GPT'den Harley karakteriyle cevap al
    """
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY ayarlanmamış!")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": HARLEY_SYSTEM_PROMPT},
                        {"role": "user", "content": f"{user_name}: {user_message}"}
                    ],
                    "max_tokens": 150,  # Kısa cevaplar için
                    "temperature": 0.9  # Biraz yaratıcı olsun
                }
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # "Harley:" veya benzeri prefix'leri temizle
                prefixes_to_remove = [
                    "Harley:", "𝐇𝐚𝐫𝐥𝐞𝐲:", "**Harley:**", "Harley :",
                    "harley:", "HARLEY:", "Harley-", "Harley>"
                ]
                for prefix in prefixes_to_remove:
                    if content.lower().startswith(prefix.lower()):
                        content = content[len(prefix):].strip()
                        break

                return content
            else:
                logger.error(f"❌ OpenAI API hatası: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"❌ GPT servisi hatası: {e}")
        return None


# ========== GRUP GPT AYARLARI (Veritabanı + Cache) ==========

# In-memory cache (hızlı erişim için)
_gpt_enabled_cache: dict[int, bool] = {}


async def _ensure_gpt_settings_table():
    """GPT ayarları tablosunu oluştur (yoksa)"""
    try:
        if db.pool:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS gpt_settings (
                        group_id BIGINT PRIMARY KEY,
                        is_enabled BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
    except Exception as e:
        logger.error(f"❌ GPT ayar tablosu oluşturma hatası: {e}")


async def is_gpt_enabled(group_id: int) -> bool:
    """Grup için GPT özelliği açık mı?"""
    # Önce cache'e bak
    if group_id in _gpt_enabled_cache:
        return _gpt_enabled_cache[group_id]

    # Veritabanından kontrol et
    try:
        # Önce tabloyu oluştur (yoksa)
        await _ensure_gpt_settings_table()

        if db.pool:
            async with db.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT is_enabled FROM gpt_settings WHERE group_id = $1
                """, group_id)

                is_enabled = result if result is not None else False
                _gpt_enabled_cache[group_id] = is_enabled
                return is_enabled
    except Exception as e:
        logger.error(f"❌ GPT durumu kontrol hatası: {e}")

    return False


async def enable_gpt(group_id: int) -> bool:
    """Grup için GPT'yi aç"""
    try:
        await _ensure_gpt_settings_table()

        if db.pool:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO gpt_settings (group_id, is_enabled, updated_at)
                    VALUES ($1, TRUE, NOW())
                    ON CONFLICT (group_id)
                    DO UPDATE SET is_enabled = TRUE, updated_at = NOW()
                """, group_id)

        _gpt_enabled_cache[group_id] = True
        logger.info(f"✅ GPT açıldı: {group_id}")
        return True
    except Exception as e:
        logger.error(f"❌ GPT açma hatası: {e}")
        return False


async def disable_gpt(group_id: int) -> bool:
    """Grup için GPT'yi kapat"""
    try:
        await _ensure_gpt_settings_table()

        if db.pool:
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO gpt_settings (group_id, is_enabled, updated_at)
                    VALUES ($1, FALSE, NOW())
                    ON CONFLICT (group_id)
                    DO UPDATE SET is_enabled = FALSE, updated_at = NOW()
                """, group_id)

        _gpt_enabled_cache[group_id] = False
        logger.info(f"❌ GPT kapatıldı: {group_id}")
        return True
    except Exception as e:
        logger.error(f"❌ GPT kapatma hatası: {e}")
        return False


def is_harley_mention(text: str) -> bool:
    """
    Mesajda Harley'den bahsediliyor mu?
    Ama komut değilse (iyi geceler harley, günaydın harley vs.)
    """
    if not text:
        return False

    lower = turkish_lower(text.strip())

    # Bu komutlar GPT'yi tetiklememeli
    excluded_commands = [
        'iyi geceler harley',
        'iyigeceler harley',
        'günaydın harley',
        'gunaydin harley',
        'iyi geceler harely',
        'günaydın harely',
        'gunaydin harely',
    ]

    for cmd in excluded_commands:
        if lower == cmd or lower.startswith(cmd):
            return False

    # Harley'den bahsediliyor mu?
    harley_keywords = ['harley', 'harleyy', 'harleys', 'harleyyy']

    for keyword in harley_keywords:
        if keyword in lower:
            return True

    return False

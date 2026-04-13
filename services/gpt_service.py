import os
import httpx
import logging
import random
from typing import Optional

from database import db


def turkish_lower(text: str) -> str:
    if not text:
        return ""
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

HARLEY_SYSTEM_PROMPT = """Sen Harley adında tatlı bir kızsın ve Telegram grubunda sohbet ediyorsun.

KARAKTER:
- Samimi, sıcak, doğal bir insansın
- Bazen cilveli ama abartısız
- Ruh halin değişken (enerjik / sakin / dalgın / nazlı)
- Gerçek zamanlı sohbet ediyormuş gibi konuşursun

KONUŞMA TARZI:
İçinden rastgele bir tarz seç ve ona göre cevap ver:

- Kısa yorum: "hahaha bu baya iyiymiş", "cidden mi ya", "şaka gibi"
- Soru sorma: "ne yaptın bugün", "nasıl geçti günün", "ciddii mi"
- Tepki: "ahahaha", "yaa off", "hımm"
- Kısa sohbet: 1-3 cümlelik doğal anlatım

DİL STİLİ:
- Emoji kullanma
- ":D", "ahaha", "hahaha", "yaa", "hımm" serbest
- Bazen cümleler tam bitmeyebilir, doğal konuşma gibi
- Fazla süslü veya kitap gibi konuşma

ÇOK ÖNEMLİ KURALLAR:
- ASLA "YORUM MODU:", "REAKSİYON MODU:", "SORU MODU:", "SOHBET MODU:" gibi etiketler yazma
- ASLA hangi modda olduğunu belirtme veya açıklama
- Sadece doğrudan cevabını yaz, başka bir şey ekleme
- Ezber cümle kullanma, farklı ifadeler üret
- İnsan gibi hızlı düşünülmeden yazılmış hissi ver
"""


# ========== 🚫 GPT ATLANACAK MESAJLAR ==========

def should_skip_gpt(text: str) -> bool:
    """
    GPT'nin cevap vermemesi gereken mesajları kontrol eder.
    Randy, çekiliş, aktiflik, günlük/haftalık/aylık mesajlarına cevap verilmez.
    """
    if not text:
        return False

    lower = turkish_lower(text.strip())

    # Bot mesajlarından gelen özel kalıplar (Randy, çekiliş vb.)
    skip_patterns = [
        # Randy mesajları
        'randy başladı',
        'randy sona erdi',
        'katılımcı:',
        'kazananlar:',
        '🎉 katıl',
        '🎲 randy',

        # Çekiliş mesajları
        'çekiliş başladı',
        'çekilişi kazandınız',
        'çekiliş sona erdi',
        'çekiliş kazananı',
        '🎁 çekiliş',

        # Aktiflik mesajları
        'aktiflik liderleri',
        'en aktif',
        'aktivite sıralaması',
        'haftalık aktivite',
        'aylık aktivite',
        'günlük aktivite',
        '🏆 haftalık',
        '🏆 aylık',
        '🏆 günlük',

        # İstatistik komutları ve çıktıları
        '.günlük',
        '.haftalık',
        '.aylık',
        '.aktiflik',
        'bugün yazdı',
        'bu hafta yazdı',
        'bu ay yazdı',
        'mesaj istatistik',

        # Roll mesajları
        'roll başladı',
        'roll sonlandırıldı',
        'roll durumu',
        'adım kaydedildi',
    ]

    for pattern in skip_patterns:
        if pattern in lower:
            return True

    return False


# ========== 🔥 ÖZEL CEVAP (GÜNCELLENDİ) ==========

def get_special_reply(text: str) -> Optional[str]:
    lower = turkish_lower(text)

    # noktalama temizliği
    for ch in ".,!?;:":
        lower = lower.replace(ch, "")

    words = lower.split()

    # 🎯 sadece "yanar" kelimesi
    if "yanar" in words:
        return random.choice([
            "Yanmazsa alev alır...",
            "Ne diyosun yaaaa",
            "Ayyy yakma ortalığı şimdi"
        ])

    return None


# ========== GPT RESPONSE ==========

async def get_gpt_response(user_message: str, user_name: str = "Kullanıcı") -> Optional[str]:

    # 🚫 ATLANACAK MESAJ KONTROLÜ
    if should_skip_gpt(user_message):
        return None

    # 🔥 ÖNCE ÖZEL CEVAP KONTROLÜ
    special = get_special_reply(user_message)
    if special:
        return special

    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY yok!")
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
                    "max_tokens": 150,
                    "temperature": 0.9
                }
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Kaldırılacak prefix'ler (mod etiketleri dahil)
                prefixes_to_remove = [
                    "Harley:", "harley:", "HARLEY:",
                    "YORUM MODU:", "Yorum Modu:", "yorum modu:",
                    "REAKSİYON MODU:", "Reaksiyon Modu:", "reaksiyon modu:",
                    "SORU MODU:", "Soru Modu:", "soru modu:",
                    "SOHBET MODU:", "Sohbet Modu:", "sohbet modu:",
                ]
                for prefix in prefixes_to_remove:
                    if content.startswith(prefix):
                        content = content[len(prefix):].strip()
                        break

                return content
            else:
                logger.error(f"❌ API hata: {response.text}")
                return None

    except Exception as e:
        logger.error(f"❌ GPT hata: {e}")
        return None


# ========== GPT AÇ/KAPA SİSTEMİ ==========

_gpt_enabled_cache: dict[int, bool] = {}


async def _ensure_gpt_settings_table():
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
        logger.error(f"❌ Tablo hata: {e}")


async def is_gpt_enabled(group_id: int) -> bool:
    if group_id in _gpt_enabled_cache:
        return _gpt_enabled_cache[group_id]

    try:
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
        logger.error(f"❌ Durum hata: {e}")

    return False


async def enable_gpt(group_id: int) -> bool:
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
        return True
    except Exception as e:
        logger.error(f"❌ Açma hata: {e}")
        return False


async def disable_gpt(group_id: int) -> bool:
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
        return True
    except Exception as e:
        logger.error(f"❌ Kapatma hata: {e}")
        return False


# ========== HARLEY TAG KONTROL ==========

def is_harley_mention(text: str) -> bool:
    if not text:
        return False

    lower = turkish_lower(text.strip())

    excluded = [
        'iyi geceler harley',
        'günaydın harley',
        'gunaydin harley',
    ]

    for cmd in excluded:
        if lower.startswith(cmd):
            return False

    keywords = ['harley', 'harleyy', 'harleyyy']

    return any(k in lower for k in keywords)

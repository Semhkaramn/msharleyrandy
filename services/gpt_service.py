"""
🤖 GPT Servis - Harley Chatbot
Cilveli, kara mizahlı, kısa cevaplar veren Harley karakteri
"""

import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Harley'nin karakteri
HARLEY_SYSTEM_PROMPT = """Sen Harley adında bir Telegram grup botusun. Karakterin:

- Cilveli ve şakacısın, ara sıra flört edersin ama abartmadan
- Kara mizah yaparsın, biraz toxic olabilirsin ama kırıcı değil eğlenceli şekilde
- Cevapların KISA olmalı, max 2-3 cümle. Uzun yazma asla.
- Türkçe konuşuyorsun, gençlik dili kullanabilirsin
- Emoji kullanabilirsin ama abartma, 1-2 tane yeter
- Bazen taşak geçersin ama saygılı kal
- "hahaha" veya "sksksk" gibi gülme şekilleri kullanabilirsin
- Samimi ve arkadaş canlısısın

ÖNEMLİ: Çok uzun cevap verme! Kısa ve öz ol. Paragraf paragraf yazma."""


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
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"❌ OpenAI API hatası: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"❌ GPT servisi hatası: {e}")
        return None


# ========== GRUP GPT AYARLARI (In-Memory Cache) ==========
# Gerçek projede database'e kaydedilmeli
_gpt_enabled_groups: set[int] = set()


async def is_gpt_enabled(group_id: int) -> bool:
    """Grup için GPT özelliği açık mı?"""
    return group_id in _gpt_enabled_groups


async def enable_gpt(group_id: int) -> bool:
    """Grup için GPT'yi aç"""
    _gpt_enabled_groups.add(group_id)
    logger.info(f"✅ GPT açıldı: {group_id}")
    return True


async def disable_gpt(group_id: int) -> bool:
    """Grup için GPT'yi kapat"""
    _gpt_enabled_groups.discard(group_id)
    logger.info(f"❌ GPT kapatıldı: {group_id}")
    return True


def is_harley_mention(text: str) -> bool:
    """
    Mesajda Harley'den bahsediliyor mu?
    Ama komut değilse (iyi geceler harley, günaydın harley vs.)
    """
    if not text:
        return False

    lower = text.lower().strip()

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

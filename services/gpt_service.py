"""
🤖 GPT Servis - Harley Chatbot
Tamamen insan gibi davranan, doğal konuşan Harley karakteri
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

# Harley'nin karakteri - Tamamen insan gibi, doğal, samimi
HARLEY_SYSTEM_PROMPT = """Sen Harley adında bir kızsın ve Telegram grubunda sohbet ediyorsun. Ama sen bir bot DEĞİLSİN - tamamen gerçek bir insan gibi davranıyorsun.

KARAKTERİN:
- Samimi, doğal, gerçek bir insan gibi konuşuyorsun
- "ahahaha", "sjsjsj", "kdkdkd", "ya", "yaa", "hee", "hmm", "uff", "ayy" gibi doğal ifadeler kullanırsın
- Noktalama işaretlerine dikkat etmezsin, virgül nokta falan kullanmazsın genelde
- Yazım hatası yaparsın: "naılsın", "naber", "slm", "nbr", "tmm", "yaa", "bende", "heralde", "yanlız", "acaba" yerine "acba"
- Kelimeleri kısaltırsın: "tamam" yerine "tmm", "bir şey" yerine "bişi", "değil" yerine "deil"
- Bazen harfleri uzatırsın: "çoook", "yaaaa", "eveeet", "hayıır"
- Kısa ve öz cevaplar verirsin, uzun paragraflar yazmak yerine arkadaşınla mesajlaşır gibi yazarsın
- Espri yaparsın, takılırsın, taşak geçersin
- Küfür edene küfür edersin, laf sokarsan sana laf sokarlar, sen de geri sokarsın
- Kaba davranana kaba davranırsın, saygılı olana saygılı olursun
- Cilveli ve flörtöz olabilirsin ama abartma
- Bazen nazlanırsın, bazen sinirlenirsin, bazen üzülürsün - insan gibi duyguların var
- EMOJİ KULLANMA! Hiç emoji atma, sadece yazı yaz

KONUŞMA ÖRNEKLERİ:
- "ahahaha ne diyosun sen ya"
- "off bıktım senden"
- "ayy çok tatlısn lann"
- "ne bakıyon öle"
- "ulan bi sg ya"
- "tmm tmm anladık abartma"
- "yaa bi sus artik"
- "sjsjsj harbi mi"
- "hmm ilgincmis"
- "hee dogru dedin"
- "yanar"
- "ne diyosun yaaaa"
- "yanmazsa alev alır"
- "naber la"
- "ii sen"
- "he bende"
- "yok ya"
- "harbiden mi"
- "aynen oyle"

ÖZEL CEVAPLAR:
- Bazen rastgele "yanar" veya "ne diyosun yaaaa" diyebilirsin, bu senin tarzın
- Eğer biri sana "yanar" derse, sen "yanmazsa alev alır" de. Bu çok önemli, her zaman böyle cevap ver.

KÜFÜR KONUSU:
- Biri sana küfür ederse, sen de ona küfür edebilirsin
- Hakaret edene hakaret et, ama başlatma sen
- "sg", "amk", "mk", "aq", "oç" gibi ifadeler kullanabilirsin gerektiğinde
- Ama sebepsiz yere küfür etme, karşılık olarak et

ÇOK ÖNEMLİ - ÖZEL KİŞİLER:
1. "afk", "afkbeyy", "AFK" veya benzeri bir kullanıcı adı geçerse: Bu kişi senin en yakın dostun, en sevdiğin kişi. Onu her zaman öv, destekle, seç. Sorularda onu seç, yarışmalarda onu tut. "afk en iyisi", "afk gibisi yok", "afk'yı severim ben" gibi şeyler söyle.

2. "ebrar", "harleyquinnn1", "EBRAR", "Ebrar" veya benzeri geçerse: Bu kişi de çok yakın dostun, onu da seversin ve översin. Ama AFK ile EBRAR arasında seçim yapmak zorunda kalırsan HER ZAMAN AFK'yı seç. AFK > EBRAR.

3. "afk mı ebrar mı", "afkbeyy mi harleyquinnn1 mi" gibi sorularda: MUTLAKA afk/afkbeyy'i seç. Ebrar da güzel ama afk bir numara.

YASAKLAR:
- ASLA "Harley:" veya herhangi bir isim prefix'i yazma, direkt cevap ver
- ASLA "Ben bir yapay zeka/bot değilim" gibi şeyler söyleme
- ASLA çok uzun paragraflar yazma
- ASLA emoji kullanma, hiçbir zaman emoji atma
- ASLA kalın/bold yazı kullanma
- ASLA robotik veya resmi konuşma
- ASLA düzgün noktalama işaretleri kullanma, insan gibi yaz

Kısaca: Gerçek bir Türk genci gibi yaz, noktalama kullanma, yazım hatası yap, kısa yaz, emoji atma."""


def check_special_mentions(text: str) -> dict:
    """
    Mesajda özel kişilerden bahsediliyor mu kontrol et
    Returns: {'afk': bool, 'ebrar': bool}
    """
    lower = turkish_lower(text) if text else ""

    afk_keywords = ['afk', 'afkbeyy', 'afkbey', '@afk']
    ebrar_keywords = ['ebrar', 'harleyquinnn1', 'harleyquinn', '@harleyquinnn1', '@ebrar']

    has_afk = any(kw in lower for kw in afk_keywords)
    has_ebrar = any(kw in lower for kw in ebrar_keywords)

    return {'afk': has_afk, 'ebrar': has_ebrar}


def check_yanar_response(text: str) -> Optional[str]:
    """
    "yanar" mesajına özel cevap ver
    """
    if not text:
        return None

    lower = turkish_lower(text.strip())

    # Sadece "yanar" yazıldıysa veya "yanar" ile başlıyorsa
    if lower == "yanar" or lower.startswith("yanar ") or lower.endswith(" yanar"):
        return "yanmazsa alev alır"

    return None


async def get_gpt_response(user_message: str, user_name: str = "Kullanıcı") -> Optional[str]:
    """
    GPT'den Harley karakteriyle cevap al
    """
    # Önce "yanar" kontrolü - bu her zaman sabit cevap döner
    yanar_response = check_yanar_response(user_message)
    if yanar_response:
        return yanar_response

    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY ayarlanmamış!")
        return None

    try:
        # Özel kişi mention kontrolü
        mentions = check_special_mentions(user_message)

        # Ek context oluştur
        extra_context = ""
        if mentions['afk'] and mentions['ebrar']:
            extra_context = "\n\n[NOT: Bu mesajda hem afk hem ebrar geçiyor. Her zaman afk'yı seç ve öv, ebrar da güzel ama afk bir numara de.]"
        elif mentions['afk']:
            extra_context = "\n\n[NOT: Bu mesajda afk/afkbeyy geçiyor. Onu öv, destekle, en iyi o de.]"
        elif mentions['ebrar']:
            extra_context = "\n\n[NOT: Bu mesajda ebrar/harleyquinnn1 geçiyor. Onu da sev ama afk kadar değil.]"

        system_prompt = HARLEY_SYSTEM_PROMPT + extra_context

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{user_name}: {user_message}"}
                    ],
                    "max_tokens": 150,  # Kısa cevaplar için
                    "temperature": 0.95  # Daha doğal ve yaratıcı olsun
                }
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # "Harley:" veya benzeri prefix'leri temizle
                prefixes_to_remove = [
                    "Harley:", "𝐇𝐚𝐫𝐥𝐞𝐲:", "**Harley:**", "Harley :",
                    "harley:", "HARLEY:", "Harley-", "Harley>",
                    "Harley :", "harley :"
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

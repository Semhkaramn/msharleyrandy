"""
🏷️ Etiketleme Servisi
Kullanıcıları mention ile etiketler
- /etiket: 5'erli grup halinde etiketleme
- /naber: Tek tek rastgele cümlelerle etiketleme
- Otomatik etiketleme: Ayarlanabilir aralıklarla otomatik etiket
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from database import db
from telegram import Bot
from telegram.error import RetryAfter, TelegramError, BadRequest
from utils.logger import get_logger

# Logger
logger = get_logger(__name__)

# Aktif etiketleme işlemleri (grup bazlı)
# {group_id: {"type": "etiket"|"naber", "active": True, "task": asyncio.Task}}
active_tagging_sessions: Dict[int, Dict[str, Any]] = {}

# Otomatik etiketleme görevleri (grup bazlı)
# {group_id: {"active": True, "task": asyncio.Task, "interval": int}}
auto_tagging_tasks: Dict[int, Dict[str, Any]] = {}


# /naber için rastgele mesajlar - Cana yakın, merak uyandırıcı, samimi
NABER_MESSAGES = [
    # === MERAK UYANDIRAN ===
    "sana bi şey söylicem",
    "bi dakika",
    "dur dur dur",
    "tahmin et ne oldu",
    "biliyor musun ne düşündüm",
    "çok ilginç bi şey var",
    "duydum duydum",
    "sana bi soru sorucam",
    "acil gel",
    "bi saniye",
    "haberin var mı",
    "dur anlatıyım",
    "çok garip bi şey fark ettim",
    "bunu görmek zorundasın",
    "yok artık ya",
    "şaka mı bu",
    "cidden mi",
    "inanmıyorum",
    "bak bak bak",
    "gel bakıyım buraya",

    # === SICAK & SAMİMİ ===
    "canım benim",
    "tatlım",
    "güzelim",
    "naber hayatım",
    "aşkım naptın",
    "özledim senii",
    "nerelerdesin be",
    "görünsene bi",
    "kaçma benden",
    "hadi gel konuşalım",
    "seni arıyordum",
    "tam seni düşünüyordum",
    "aklıma geldin",
    "nasılsın bakalım",
    "iyi misin sen",

    # === ENERJİK & EĞLENCELİ ===
    "heyy",
    "heyyy selamm",
    "yooo",
    "alooo",
    "buradayım",
    "selammm",
    "merhabaa",
    "naberr",
    "neşeli misin",
    "keyifler nasıl",
    "gülümsüyor musun",
    "mutlu musun",
    "harika bi gün değil mi",

    # === DOĞAL & RAHAT ===
    "napıyon",
    "naber la",
    "nası gidiyo",
    "ne var ne yok",
    "nasıl gidiyor",
    "her şey yolunda mı",
    "hayat nasıl",
    "sıkıldın mı yoksa",
    "canın sıkılıyo mu",
    "boş musun",

    # === DAVET EDEN ===
    "gel bi muhabbet edelim",
    "sohbet edelim mi",
    "konuşalım mı",
    "takılalım mı biraz",
    "bi çay içelim mi",
    "gel seni dinliyim",
    "anlat bakalım",
    "ne düşünüyosun",

    # === İLGİ ÇEKİCİ ===
    "psst",
    "hey sen",
    "bi baksana",
    "buraya bak",
    "dikkat",
    "sana diyorum",
    "duydun mu beni",
    "görüyor musun",
    "yazıyorum işte",
    "sesimi duyuyor musun",

    # === SEVİMLİ ===
    "hiii",
    "selam tatlı şey",
    "merhaba güzel insan",
    "nasılsın bi tanem",
    "iyi akşamlar güzellik",
    "günaydın tatlım",
]


async def check_user_in_group(bot: Bot, group_id: int, user_id: int) -> bool:
    """
    Kullanıcının hala grupta olup olmadığını kontrol et

    Args:
        bot: Telegram bot instance
        group_id: Grup ID
        user_id: Kullanıcı ID

    Returns:
        bool: Grupta ise True, değilse False
    """
    try:
        member = await bot.get_chat_member(group_id, user_id)
        # left, kicked, banned durumları grupta olmadığını gösterir
        if member.status in ['left', 'kicked', 'banned']:
            return False
        return True
    except BadRequest as e:
        # Kullanıcı bulunamadı veya erişim yok
        if "user not found" in str(e).lower() or "user_not_participant" in str(e).lower():
            return False
        return False
    except TelegramError:
        # Diğer hatalar - güvenli tarafta kal, kullanıcıyı etiketleme
        return False


async def remove_user_from_db(group_id: int, user_id: int) -> bool:
    """
    Kullanıcıyı veritabanından sil

    Args:
        group_id: Grup ID
        user_id: Kullanıcı ID

    Returns:
        bool: Başarılı ise True
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM telegram_users
                WHERE group_id = $1 AND telegram_id = $2
            """, group_id, user_id)
            logger.info(f"Kullanıcı silindi: {user_id} (Grup: {group_id})")
            return True
    except Exception as e:
        logger.error(f"Kullanıcı silme hatası: {e}")
        return False


async def get_verified_group_users(bot: Bot, group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki DOĞRULANMIŞ kullanıcıları getir.
    Her kullanıcının hala grupta olup olmadığını kontrol eder.
    Grupta olmayanları veritabanından SİLER.

    Bu fonksiyon etiketleme ve sıralama işlemlerinde kullanılmalıdır.

    Args:
        bot: Telegram bot instance
        group_id: Telegram grup ID

    Returns:
        List[Dict]: Grupta olan aktif kullanıcı listesi
    """
    all_users = await get_group_users(group_id)

    if not all_users:
        return []

    # Tüm kullanıcıları paralel olarak kontrol et (N+1 sorunu çözümü)
    check_tasks = [
        check_user_in_group(bot, group_id, user['telegram_id'])
        for user in all_users
    ]
    results = await asyncio.gather(*check_tasks, return_exceptions=True)

    verified_users = []
    users_to_remove = []

    for user, is_in_group in zip(all_users, results):
        # Hata durumunda kullanıcıyı tutmaya devam et
        if isinstance(is_in_group, Exception):
            verified_users.append(user)
            continue

        if is_in_group:
            verified_users.append(user)
        else:
            users_to_remove.append(user['telegram_id'])

    # Grupta olmayan kullanıcıları paralel olarak sil
    if users_to_remove:
        remove_tasks = [
            remove_user_from_db(group_id, user_id)
            for user_id in users_to_remove
        ]
        await asyncio.gather(*remove_tasks, return_exceptions=True)
        logger.info(f"Temizlik: {len(users_to_remove)} kullanıcı gruptan çıkmış/banlanmış - silindi (Grup: {group_id})")

    return verified_users


async def cleanup_group_users(bot: Bot, group_id: int) -> int:
    """
    Gruptaki tüm kullanıcıları kontrol edip çıkanları/banlananları temizle.
    Periyodik temizlik veya manuel temizlik için kullanılır.

    Args:
        bot: Telegram bot instance
        group_id: Telegram grup ID

    Returns:
        int: Silinen kullanıcı sayısı
    """
    all_users = await get_group_users(group_id)

    if not all_users:
        return 0

    # Tüm kullanıcıları paralel olarak kontrol et (N+1 sorunu çözümü)
    check_tasks = [
        check_user_in_group(bot, group_id, user['telegram_id'])
        for user in all_users
    ]
    results = await asyncio.gather(*check_tasks, return_exceptions=True)

    users_to_remove = []

    for user, is_in_group in zip(all_users, results):
        # Hata durumunda kullanıcıyı silme
        if isinstance(is_in_group, Exception):
            continue

        if not is_in_group:
            users_to_remove.append(user['telegram_id'])

    # Grupta olmayan kullanıcıları paralel olarak sil
    if users_to_remove:
        remove_tasks = [
            remove_user_from_db(group_id, user_id)
            for user_id in users_to_remove
        ]
        await asyncio.gather(*remove_tasks, return_exceptions=True)
        logger.info(f"Manuel Temizlik: {len(users_to_remove)} kullanıcı silindi (Grup: {group_id})")

    return len(users_to_remove)


async def get_group_users(group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki kayıtlı kullanıcıları getir

    Args:
        group_id: Telegram grup ID

    Returns:
        List[Dict]: Kullanıcı listesi
    """
    try:
        async with db.pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, last_name
                FROM telegram_users
                WHERE group_id = $1
                ORDER BY message_count DESC
            """, group_id)

            return [dict(u) for u in users]
    except Exception as e:
        logger.error(f"Kullanıcı listesi getirme hatası: {e}")
        return []


async def get_active_group_users(bot: Bot, group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki AKTİF kullanıcıları getir (grupta olanlar)
    NOT: Artık kullanıcıları veritabanından SİLMİYOR, sadece etiketleme listesinden atlıyor
    Mesaj geçmişi korunur!

    Args:
        bot: Telegram bot instance
        group_id: Telegram grup ID

    Returns:
        List[Dict]: Aktif kullanıcı listesi
    """
    all_users = await get_group_users(group_id)
    active_users = []

    for user in all_users:
        user_id = user['telegram_id']

        # Kullanıcının grupta olup olmadığını kontrol et
        is_in_group = await check_user_in_group(bot, group_id, user_id)

        if is_in_group:
            active_users.append(user)
        # NOT: Grupta olmayan kullanıcılar artık SİLİNMİYOR!
        # Sadece etiketleme listesinden atlanıyor, mesaj geçmişi korunuyor

    return active_users


def format_user_mention(user: Dict[str, Any]) -> str:
    """
    Kullanıcıyı mention formatında döndür
    Her zaman tıklanabilir tg://user formatı kullanır (username olsa da olmasa da)
    Username varsa onu, yoksa first_name gösterir

    Args:
        user: Kullanıcı dict'i

    Returns:
        str: Mention formatı
    """
    telegram_id = user['telegram_id']
    username = user.get('username')
    first_name = user.get('first_name')

    # Görüntülenecek ismi belirle - username öncelikli
    if username:
        display_name = f"@{username}"
    elif first_name:
        display_name = first_name
    else:
        display_name = "Kullanıcı"

    # Her zaman tıklanabilir mention kullan (username olsa da olmasa da çalışır)
    return f'<a href="tg://user?id={telegram_id}">{display_name}</a>'


def is_tagging_active(group_id: int) -> bool:
    """
    Grupta aktif etiketleme var mı kontrol et
    """
    session = active_tagging_sessions.get(group_id)
    return session is not None and session.get('active', False)


def stop_tagging(group_id: int) -> bool:
    """
    Gruptaki aktif etiketleme işlemini durdur

    Returns:
        bool: Durduruldu mu
    """
    session = active_tagging_sessions.get(group_id)

    if not session:
        return False

    session['active'] = False

    # Task'ı iptal et
    task = session.get('task')
    if task and not task.done():
        task.cancel()

    # Session'ı temizle
    active_tagging_sessions.pop(group_id, None)

    return True


async def start_etiket_tagging(
    group_id: int,
    message: str,
    bot,
    initial_message,
    custom_emoji_text: str = None,
    message_entities: list = None
) -> bool:
    """
    /etiket komutu - 5'erli mention etiketleme başlat
    Premium emoji destekli
    Kullanıcılar rastgele sıralanır
    Grupta olmayan kullanıcılar otomatik atlanır ve silinir

    Args:
        group_id: Grup ID
        message: Etiketleme mesajı
        bot: Telegram bot instance
        initial_message: İlk mesaj objesi (silmek için)
        custom_emoji_text: Kullanıcının gönderdiği orijinal metin (premium emoji için)
        message_entities: Mesajdaki entity'ler (custom_emoji için)

    Returns:
        bool: Başlatıldı mı
    """
    # Zaten aktif mi?
    if is_tagging_active(group_id):
        return False

    # Kullanıcıları getir ve grupta olmayanları temizle
    users = await get_verified_group_users(bot, group_id)

    if not users:
        return False

    # Kullanıcıları rastgele karıştır (her seferinde farklı sıra)
    random.shuffle(users)

    # Session başlat
    active_tagging_sessions[group_id] = {
        'type': 'etiket',
        'active': True,
        'task': None
    }

    # Premium emoji'leri HTML formatına çevir (orijinal metin korunarak)
    final_message = message

    if message_entities and custom_emoji_text:
        # Orijinal metni kullan (komuttan sonraki kısım)
        original_text = custom_emoji_text

        # /etiket komutunu bul ve offset'i hesapla
        cmd_offset = 0
        if original_text.startswith("/etiket "):
            cmd_offset = len("/etiket ")
        elif original_text.startswith("/etiket"):
            cmd_offset = len("/etiket")

        # Custom emoji entity'lerini bul
        custom_emoji_entities = [e for e in message_entities if e.type == "custom_emoji"]

        if custom_emoji_entities:
            # Entity'leri sondan başa sırala (offset'ler bozulmasın)
            sorted_entities = sorted(custom_emoji_entities, key=lambda e: e.offset, reverse=True)

            # Orijinal metinden mesaj kısmını al
            msg_text = original_text[cmd_offset:] if cmd_offset > 0 else message

            # Her emoji'yi HTML formatına çevir
            for entity in sorted_entities:
                emoji_start = entity.offset - cmd_offset
                emoji_end = emoji_start + entity.length

                if emoji_start >= 0 and emoji_end <= len(msg_text):
                    # Emoji karakterini al
                    emoji_char = msg_text[emoji_start:emoji_end]
                    # HTML formatına çevir
                    emoji_html = f'<tg-emoji emoji-id="{entity.custom_emoji_id}">{emoji_char}</tg-emoji>'
                    # Metinde değiştir
                    msg_text = msg_text[:emoji_start] + emoji_html + msg_text[emoji_end:]

            final_message = msg_text.strip()

    # Mesaj boşsa varsayılan
    if not final_message:
        final_message = "🎉 Selamlar!"

    async def tagging_task():
        try:
            # İlk komutu sil
            try:
                await initial_message.delete()
            except TelegramError:
                pass

            # 5'erli gruplar halinde etiketle (kullanıcılar zaten karıştırıldı)
            batch_size = 5

            for i in range(0, len(users), batch_size):
                # Durduruldu mu kontrol et
                session = active_tagging_sessions.get(group_id)
                if not session or not session.get('active'):
                    break

                batch = users[i:i + batch_size]
                mentions = [format_user_mention(u) for u in batch]

                text = f"{final_message}\n\n" + " ".join(mentions)

                try:
                    await bot.send_message(
                        group_id,
                        text,
                        parse_mode="HTML"
                    )
                except RetryAfter as e:
                    # Flood control - bekle ve tekrar dene
                    wait_time = e.retry_after + 2
                    logger.info(f"Flood control, {wait_time} saniye bekleniyor...")
                    await asyncio.sleep(wait_time)
                    # Tekrar dene
                    try:
                        await bot.send_message(
                            group_id,
                            text,
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                except TelegramError as e:
                    logger.error(f"Etiket mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme (artırıldı)
                await asyncio.sleep(4)

            # Bittiğinde session'ı temizle
            active_tagging_sessions.pop(group_id, None)

        except asyncio.CancelledError:
            # İptal edildi
            pass
        except Exception as e:
            logger.error(f"Etiketleme hatası: {e}")
            active_tagging_sessions.pop(group_id, None)

    # Task'ı başlat
    task = asyncio.create_task(tagging_task())
    active_tagging_sessions[group_id]['task'] = task

    return True


async def start_naber_tagging(
    group_id: int,
    bot,
    initial_message
) -> bool:
    """
    /naber komutu - Tek tek rastgele cümlelerle etiketleme
    Kullanıcılar rastgele sıralanır
    Grupta olmayan kullanıcılar otomatik atlanır ve silinir

    Args:
        group_id: Grup ID
        bot: Telegram bot instance
        initial_message: İlk mesaj objesi (silmek için)

    Returns:
        bool: Başlatıldı mı
    """
    # Zaten aktif mi?
    if is_tagging_active(group_id):
        return False

    # Kullanıcıları getir ve grupta olmayanları temizle
    users = await get_verified_group_users(bot, group_id)

    if not users:
        return False

    # Kullanıcıları rastgele karıştır (her seferinde farklı sıra)
    random.shuffle(users)

    # Session başlat
    active_tagging_sessions[group_id] = {
        'type': 'naber',
        'active': True,
        'task': None
    }

    async def naber_task():
        try:
            # İlk komutu sil
            try:
                await initial_message.delete()
            except TelegramError:
                pass

            # Mesajları karıştır (her seferinde farklı sıra)
            shuffled_messages = NABER_MESSAGES.copy()
            random.shuffle(shuffled_messages)
            message_index = 0

            # Her kullanıcıyı tek tek etiketle (kullanıcılar zaten karıştırıldı)
            for user in users:
                # Durduruldu mu kontrol et
                session = active_tagging_sessions.get(group_id)
                if not session or not session.get('active'):
                    break

                mention = format_user_mention(user)

                # Sırayla mesaj seç, biterse başa dön
                random_msg = shuffled_messages[message_index % len(shuffled_messages)]
                message_index += 1

                text = f"{mention} {random_msg}"

                try:
                    await bot.send_message(
                        group_id,
                        text,
                        parse_mode="HTML"
                    )
                except RetryAfter as e:
                    # Flood control - bekle ve tekrar dene
                    wait_time = e.retry_after + 2
                    logger.info(f"Flood control, {wait_time} saniye bekleniyor...")
                    await asyncio.sleep(wait_time)
                    # Tekrar dene
                    try:
                        await bot.send_message(
                            group_id,
                            text,
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                except TelegramError as e:
                    logger.error(f"Naber mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme (artırıldı)
                await asyncio.sleep(4)

            # Bittiğinde session'ı temizle
            active_tagging_sessions.pop(group_id, None)

        except asyncio.CancelledError:
            # İptal edildi
            pass
        except Exception as e:
            logger.error(f"Naber hatası: {e}")
            active_tagging_sessions.pop(group_id, None)

    # Task'ı başlat
    task = asyncio.create_task(naber_task())
    active_tagging_sessions[group_id]['task'] = task

    return True


def get_tagging_type(group_id: int) -> Optional[str]:
    """
    Aktif etiketleme tipini döndür

    Returns:
        str|None: "etiket" veya "naber" veya None
    """
    session = active_tagging_sessions.get(group_id)
    if session and session.get('active'):
        return session.get('type')
    return None


# ============================================
# 🤖 OTOMATİK ETİKETLEME SİSTEMİ
# ============================================

async def get_auto_tag_settings(group_id: int) -> Optional[Dict[str, Any]]:
    """
    Grubun otomatik etiket ayarlarını getir
    """
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow("""
                SELECT * FROM auto_tag_settings
                WHERE group_id = $1
            """, group_id)
            return dict(settings) if settings else None
    except Exception as e:
        logger.error(f"Otomatik etiket ayarları getirme hatası: {e}")
        return None


async def set_auto_tag_settings(
    group_id: int,
    enabled: bool,
    interval_minutes: int = 10,
    tag_type: str = "naber"
) -> bool:
    """
    Grubun otomatik etiket ayarlarını kaydet

    Args:
        group_id: Grup ID
        enabled: Aktif mi
        interval_minutes: Kaç dakikada bir (varsayılan 10)
        tag_type: Etiket tipi ("naber" veya "etiket")
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO auto_tag_settings (group_id, enabled, interval_minutes, tag_type, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (group_id)
                DO UPDATE SET enabled = $2, interval_minutes = $3, tag_type = $4, updated_at = NOW()
            """, group_id, enabled, interval_minutes, tag_type)
            return True
    except Exception as e:
        logger.error(f"Otomatik etiket ayarları kaydetme hatası: {e}")
        return False


async def toggle_auto_tag(group_id: int) -> tuple[bool, bool]:
    """
    Otomatik etiketi aç/kapat

    Returns:
        tuple: (başarılı mı, yeni durum)
    """
    settings = await get_auto_tag_settings(group_id)

    if settings:
        new_state = not settings['enabled']
    else:
        new_state = True  # İlk kez açılıyor

    success = await set_auto_tag_settings(
        group_id,
        enabled=new_state,
        interval_minutes=settings['interval_minutes'] if settings else 10,
        tag_type=settings['tag_type'] if settings else "naber"
    )

    return success, new_state


async def start_auto_tagging(group_id: int, bot, interval_minutes: int = 10):
    """
    Otomatik etiketleme görevini başlat

    Args:
        group_id: Grup ID
        bot: Telegram bot instance
        interval_minutes: Kaç dakikada bir
    """
    # Zaten çalışan bir görev var mı?
    if group_id in auto_tagging_tasks and auto_tagging_tasks[group_id].get('active'):
        logger.info(f"Otomatik etiket zaten çalışıyor: {group_id}")
        return

    async def auto_tag_loop():
        tag_count = 0  # Toplam etiketleme sayısı

        while True:
            try:
                # Ayarları kontrol et
                settings = await get_auto_tag_settings(group_id)

                if not settings or not settings['enabled']:
                    # Devre dışı bırakıldı, görevi sonlandır
                    logger.info(f"Otomatik etiket devre dışı: {group_id}")
                    break

                # Aktif manuel etiketleme var mı kontrol et
                if not is_tagging_active(group_id):
                    # Aktif kullanıcıları getir (grupta olmayanlar veritabanından silinir)
                    users = await get_verified_group_users(bot, group_id)
                    total_users = len(users)

                    if users:
                        # Sadece 1 kullanıcı seç (rastgele)
                        selected_user = random.choice(users)

                        tag_count += 1
                        logger.info(f"Otomatik Etiket #{tag_count} | Grup: {group_id} | 1/{total_users} kullanıcı")

                        # Seçilen kullanıcıya rastgele mesaj gönder
                        mention = format_user_mention(selected_user)
                        random_msg = random.choice(NABER_MESSAGES)

                        try:
                            await bot.send_message(
                                group_id,
                                f"{mention} {random_msg}",
                                parse_mode="HTML"
                            )
                            logger.info(f"Otomatik Etiket #{tag_count} tamamlandı")
                        except BadRequest as e:
                            # Kullanıcı bulunamadı veya engellenmiş
                            # NOT: Artık kullanıcıyı SİLMİYORUZ, sadece log yazıyoruz
                            if "user not found" in str(e).lower() or "blocked" in str(e).lower():
                                logger.warning(f"Kullanıcıya ulaşılamadı (etiketleme atlandı): {selected_user['telegram_id']}")
                            else:
                                logger.error(f"Otomatik etiket hatası: {e}")
                        except TelegramError as e:
                            logger.error(f"Otomatik etiket hatası: {e}")
                    else:
                        logger.warning(f"Otomatik etiket: Grup {group_id}'de kullanıcı yok")
                else:
                    logger.info(f"Manuel etiketleme aktif, otomatik etiket bekliyor...")

                # Sonraki etiketleme için bekle
                # interval_minutes'a rastgele ±2 dakika ekle (daha doğal görünsün)
                wait_minutes = interval_minutes + random.randint(-2, 2)
                wait_minutes = max(3, wait_minutes)  # Minimum 3 dakika

                logger.info(f"Sonraki otomatik etiket: {wait_minutes} dakika sonra")
                await asyncio.sleep(wait_minutes * 60)

            except asyncio.CancelledError:
                logger.info(f"Otomatik etiket görevi iptal edildi: {group_id}")
                break
            except Exception as e:
                logger.error(f"Otomatik etiket döngü hatası: {e}")
                await asyncio.sleep(60)  # Hata durumunda 1 dakika bekle

        # Görev bitti, temizle
        auto_tagging_tasks.pop(group_id, None)
        logger.info(f"Otomatik etiket görevi sonlandı: {group_id} (Toplam: {tag_count} etiketleme)")

    # Görevi başlat
    task = asyncio.create_task(auto_tag_loop())
    auto_tagging_tasks[group_id] = {
        'active': True,
        'task': task,
        'interval': interval_minutes
    }
    logger.info(f"Otomatik etiket başlatıldı: Grup {group_id}, Aralık: {interval_minutes} dk")


def stop_auto_tagging(group_id: int) -> bool:
    """
    Otomatik etiketleme görevini durdur
    """
    if group_id not in auto_tagging_tasks:
        return False

    task_info = auto_tagging_tasks[group_id]
    task_info['active'] = False

    task = task_info.get('task')
    if task and not task.done():
        task.cancel()

    auto_tagging_tasks.pop(group_id, None)
    return True


def is_auto_tagging_active(group_id: int) -> bool:
    """
    Otomatik etiketleme aktif mi?
    """
    return group_id in auto_tagging_tasks and auto_tagging_tasks[group_id].get('active', False)

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


# Aktif etiketleme işlemleri (grup bazlı)
# {group_id: {"type": "etiket"|"naber", "active": True, "task": asyncio.Task}}
active_tagging_sessions: Dict[int, Dict[str, Any]] = {}

# Otomatik etiketleme görevleri (grup bazlı)
# {group_id: {"active": True, "task": asyncio.Task, "interval": int}}
auto_tagging_tasks: Dict[int, Dict[str, Any]] = {}


# /naber için rastgele cümleler - Merak uyandırıcı ve minimal emoji
NABER_MESSAGES = [
    # MERAK UYANDIRAN - GİZEMLİ
    "Sana bir şey söyleyeceğim ama...",
    "Dün gece bir şey oldu, anlatmam lazım",
    "Biliyor musun, senin hakkında bir şey duydum",
    "Bekle, sana önemli bir şey soracağım",
    "Bir sır var, söylesem mi söylemesem mi...",
    "Az önce bir şey fark ettim de...",
    "Tahmin et ne oldu?",
    "Bunu duyunca şaşıracaksın",
    "Sana bir teklifim var...",
    "Bir dakika, bu çok önemli",
    "Duydun mu son haberi?",
    "Senden bir şey isteyeceğim",
    "Bak, sana bir şey göstermem lazım",
    "Bu sadece senin için...",
    "Şşş, kimse duymasın ama...",
    "Bir planım var, katılır mısın?",
    "Sana güveniyorum, söyleyebilir miyim?",
    "Bu aramızda kalsın ama...",
    "Bir şeyi merak ediyorum...",
    "Sence de garip değil mi?",
    "Dikkat et, önemli bir şey söyleyeceğim",
    "Bunu sadece sana söylüyorum",
    "Kulağına bir şey fısıldayacağım",
    "Hadi gel, bir şey paylaşayım",

    # SORU SORAN - İLGİ ÇEKİCİ
    "Neden sessizsin, bir şey mi oldu?",
    "Sen ne düşünüyorsun bu konuda?",
    "Merak ettim, nasıl gidiyor?",
    "Bugün ne yaptın anlatsana",
    "Sence hangisi daha iyi?",
    "Bir şey sormak istiyorum",
    "Son zamanlarda neler oluyor?",
    "Bana bir şey söyle",
    "Fikrini merak ediyorum",
    "Ne zaman konuşacağız?",
    "Planların ne?",
    "Bir dakikan var mı?",
    "Seninle bir konu hakkında konuşmak istiyorum",
    "Bu durumda ne yapardın?",

    # UYANDIRICI - ENERJİK
    "Heyy neredesin?",
    "Uyan artık!",
    "Cevap versene",
    "Görüyorum seni",
    "Kaçamazsın benden",
    "Yaşıyor musun?",
    "Bir işaret ver",
    "Burada mısın?",
    "Alo, biri var mı?",
    "Dünyaya dön",
    "Kaybolma hadi",
    "Gel buraya",
    "Bekletme beni",
    "Hadi konuş",

    # SAMİMİ - SICAK
    "Nasılsın canım?",
    "Seni özledim",
    "Ne var ne yok?",
    "Seninle konuşmak istiyorum",
    "Özlettin kendini",
    "Bir şeyler anlat",
    "Naber bakayım",
    "Görüşmeyeli ne oldu?",
    "Aklıma geldin",
    "Seni merak ettim",
    "Nasıl gidiyor hayat?",
    "İyisin değil mi?",
    "Keyifler nasıl?",

    # EĞLENCE ÖNERİSİ
    "Sıkıldın mı? Gel muhabbet edelim",
    "Canın sohbet ister mi?",
    "Oyun oynayalım mı?",
    "Bir şeyler yapalım",
    "Muhabbet edelim mi?",
    "Gel takılalım",
    "Vakit geçirelim mi?",

    # KISA VE ETKİLİ
    "Hey!",
    "Psst...",
    "Bak bak",
    "Dur bir dakika",
    "Bekle",
    "Gel",
    "Dinle",
    "Baksana",
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
            print(f"🗑️ Kullanıcı silindi: {user_id} (Grup: {group_id})")
            return True
    except Exception as e:
        print(f"❌ Kullanıcı silme hatası: {e}")
        return False


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
        print(f"❌ Kullanıcı listesi getirme hatası: {e}")
        return []


async def get_active_group_users(bot: Bot, group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki AKTİF kullanıcıları getir (grupta olanlar)
    Grupta olmayanları veritabanından siler

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
        else:
            # Grupta değilse veritabanından sil
            await remove_user_from_db(group_id, user_id)
            print(f"👋 Grupta olmayan kullanıcı silindi: {user_id}")

    return active_users


def format_user_mention(user: Dict[str, Any]) -> str:
    """
    Kullanıcıyı mention formatında döndür
    Önce @username dener (daha güvenilir), yoksa tg://user formatı

    Args:
        user: Kullanıcı dict'i

    Returns:
        str: Mention formatı
    """
    telegram_id = user['telegram_id']
    username = user.get('username')
    first_name = user.get('first_name') or f"User{str(telegram_id)[-4:]}"

    # Username varsa @username kullan (daha güvenilir, her zaman çalışır)
    if username:
        return f'@{username}'

    # Username yoksa tg://user formatı kullan
    return f'<a href="tg://user?id={telegram_id}">{first_name}</a>'


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
    Grupta olmayan kullanıcıları otomatik siler

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

    # Aktif kullanıcıları getir (grupta olmayanları siler)
    users = await get_active_group_users(bot, group_id)

    if not users:
        return False

    # Session başlat
    active_tagging_sessions[group_id] = {
        'type': 'etiket',
        'active': True,
        'task': None
    }

    # Premium emoji var mı kontrol et
    has_custom_emoji = False
    emoji_html = ""

    if message_entities:
        for entity in message_entities:
            if entity.type == "custom_emoji":
                has_custom_emoji = True
                # Custom emoji ID'sini al ve HTML formatına çevir
                custom_emoji_id = entity.custom_emoji_id
                if custom_emoji_id:
                    # Telegram HTML formatı: <tg-emoji emoji-id="ID">emoji</tg-emoji>
                    emoji_html = f'<tg-emoji emoji-id="{custom_emoji_id}">✨</tg-emoji> '
                break

    async def tagging_task():
        try:
            # İlk komutu sil
            try:
                await initial_message.delete()
            except:
                pass

            # 5'erli gruplar halinde etiketle
            batch_size = 5

            for i in range(0, len(users), batch_size):
                # Durduruldu mu kontrol et
                session = active_tagging_sessions.get(group_id)
                if not session or not session.get('active'):
                    break

                batch = users[i:i + batch_size]
                mentions = [format_user_mention(u) for u in batch]

                # Premium emoji varsa onu kullan, yoksa varsayılan
                if has_custom_emoji and emoji_prefix:
                    text = f"{emoji_prefix}{message}\n\n" + " ".join(mentions)
                else:
                    text = f"💎 {message}\n\n" + " ".join(mentions)

                try:
                    await bot.send_message(
                        group_id,
                        text,
                        parse_mode="HTML"
                    )
                except RetryAfter as e:
                    # Flood control - bekle ve tekrar dene
                    wait_time = e.retry_after + 2
                    print(f"⏳ Flood control, {wait_time} saniye bekleniyor...")
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
                    print(f"❌ Etiket mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme (artırıldı)
                await asyncio.sleep(4)

            # Bittiğinde session'ı temizle
            active_tagging_sessions.pop(group_id, None)

        except asyncio.CancelledError:
            # İptal edildi
            pass
        except Exception as e:
            print(f"❌ Etiketleme hatası: {e}")
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
    Grupta olmayan kullanıcıları otomatik siler

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

    # Aktif kullanıcıları getir (grupta olmayanları siler)
    users = await get_active_group_users(bot, group_id)

    if not users:
        return False

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
            except:
                pass

            # Mesajları karıştır (her seferinde farklı sıra)
            shuffled_messages = NABER_MESSAGES.copy()
            random.shuffle(shuffled_messages)
            message_index = 0

            # Her kullanıcıyı tek tek etiketle
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
                    print(f"⏳ Flood control, {wait_time} saniye bekleniyor...")
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
                    print(f"❌ Naber mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme (artırıldı)
                await asyncio.sleep(4)

            # Bittiğinde session'ı temizle
            active_tagging_sessions.pop(group_id, None)

        except asyncio.CancelledError:
            # İptal edildi
            pass
        except Exception as e:
            print(f"❌ Naber hatası: {e}")
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
        print(f"❌ Otomatik etiket ayarları getirme hatası: {e}")
        return None


async def set_auto_tag_settings(
    group_id: int,
    enabled: bool,
    interval_minutes: int = 60,
    tag_type: str = "naber"
) -> bool:
    """
    Grubun otomatik etiket ayarlarını kaydet

    Args:
        group_id: Grup ID
        enabled: Aktif mi
        interval_minutes: Kaç dakikada bir (varsayılan 60)
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
        print(f"❌ Otomatik etiket ayarları kaydetme hatası: {e}")
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
        interval_minutes=settings['interval_minutes'] if settings else 60,
        tag_type=settings['tag_type'] if settings else "naber"
    )

    return success, new_state


async def start_auto_tagging(group_id: int, bot, interval_minutes: int = 60):
    """
    Otomatik etiketleme görevini başlat

    Args:
        group_id: Grup ID
        bot: Telegram bot instance
        interval_minutes: Kaç dakikada bir
    """
    # Zaten çalışan bir görev var mı?
    if group_id in auto_tagging_tasks and auto_tagging_tasks[group_id].get('active'):
        return

    async def auto_tag_loop():
        while True:
            try:
                # Ayarları kontrol et
                settings = await get_auto_tag_settings(group_id)

                if not settings or not settings['enabled']:
                    # Devre dışı bırakıldı, görevi sonlandır
                    break

                # Aktif manuel etiketleme var mı kontrol et
                if not is_tagging_active(group_id):
                    # Aktif kullanıcıları getir
                    users = await get_active_group_users(bot, group_id)

                    if users:
                        # Rastgele 3-7 kullanıcı seç (herkesi değil)
                        sample_size = min(random.randint(3, 7), len(users))
                        selected_users = random.sample(users, sample_size)

                        # Her kullanıcıya rastgele mesaj gönder
                        for user in selected_users:
                            mention = format_user_mention(user)
                            random_msg = random.choice(NABER_MESSAGES)

                            try:
                                await bot.send_message(
                                    group_id,
                                    f"{mention} {random_msg}",
                                    parse_mode="HTML"
                                )
                            except TelegramError as e:
                                print(f"❌ Otomatik etiket hatası: {e}")

                            # Mesajlar arası bekleme
                            await asyncio.sleep(random.randint(3, 6))

                # Sonraki etiketleme için bekle
                # interval_minutes'a rastgele ±10 dakika ekle (daha doğal görünsün)
                wait_minutes = interval_minutes + random.randint(-10, 10)
                wait_minutes = max(15, wait_minutes)  # Minimum 15 dakika

                await asyncio.sleep(wait_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Otomatik etiket döngü hatası: {e}")
                await asyncio.sleep(60)  # Hata durumunda 1 dakika bekle

        # Görev bitti, temizle
        auto_tagging_tasks.pop(group_id, None)

    # Görevi başlat
    task = asyncio.create_task(auto_tag_loop())
    auto_tagging_tasks[group_id] = {
        'active': True,
        'task': task,
        'interval': interval_minutes
    }


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

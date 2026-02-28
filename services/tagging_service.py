"""
🏷️ Etiketleme Servisi
Kullanıcıları mention ile etiketler
- /etiket: 5'erli grup halinde etiketleme
- /naber: Tek tek rastgele cümlelerle etiketleme
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from database import db


# Aktif etiketleme işlemleri (grup bazlı)
# {group_id: {"type": "etiket"|"naber", "active": True, "task": asyncio.Task}}
active_tagging_sessions: Dict[int, Dict[str, Any]] = {}


# /naber için rastgele cümleler - Premium emojilerle
NABER_MESSAGES = [
    "Naber? 🔥",
    "Nasılsın? ✨",
    "Ne yapıyorsun? 💫",
    "Selam! 🌟",
    "Hey! 💎",
    "Naber dostum? 🎯",
    "Nasıl gidiyor? 🚀",
    "Ne var ne yok? 💥",
    "Selam canım! 💖",
    "Heyy! 🌈",
    "Naber kanka? 🔱",
    "Nasılsın bakalım? ⚡",
    "Eee naber? 🎭",
    "Ne haber? 🎪",
    "Selamlar! 🎨",
    "Hey dostum! 🏆",
    "Naber kardeşim? 👑",
    "Nasılsın güzelim? 💝",
    "Ne yapıyosun? 🎬",
    "Selam aşkım! 💕",
]


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


def format_user_mention(user: Dict[str, Any]) -> str:
    """
    Kullanıcıyı mention formatında döndür

    Args:
        user: Kullanıcı dict'i

    Returns:
        str: HTML mention formatı
    """
    telegram_id = user['telegram_id']
    first_name = user.get('first_name') or user.get('username') or f"User{str(telegram_id)[-4:]}"

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
    initial_message
) -> bool:
    """
    /etiket komutu - 5'erli mention etiketleme başlat

    Args:
        group_id: Grup ID
        message: Etiketleme mesajı
        bot: Telegram bot instance
        initial_message: İlk mesaj objesi (silmek için)

    Returns:
        bool: Başlatıldı mı
    """
    # Zaten aktif mi?
    if is_tagging_active(group_id):
        return False

    # Kullanıcıları getir
    users = await get_group_users(group_id)

    if not users:
        return False

    # Session başlat
    active_tagging_sessions[group_id] = {
        'type': 'etiket',
        'active': True,
        'task': None
    }

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

                # Premium emojilerle mesaj oluştur
                text = f"💎 {message}\n\n" + " ".join(mentions)

                try:
                    await bot.send_message(
                        group_id,
                        text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"❌ Etiket mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme
                await asyncio.sleep(1.5)

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

    # Kullanıcıları getir
    users = await get_group_users(group_id)

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

            # Her kullanıcıyı tek tek etiketle
            for user in users:
                # Durduruldu mu kontrol et
                session = active_tagging_sessions.get(group_id)
                if not session or not session.get('active'):
                    break

                mention = format_user_mention(user)
                random_msg = random.choice(NABER_MESSAGES)

                text = f"{mention} {random_msg}"

                try:
                    await bot.send_message(
                        group_id,
                        text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"❌ Naber mesaj gönderme hatası: {e}")

                # Flood önleme - mesajlar arası bekleme (biraz daha uzun)
                await asyncio.sleep(2)

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

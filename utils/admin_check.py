"""
🔒 Admin Kontrolü
Telegram API ile admin kontrolü ve cache yönetimi
"""

from typing import Optional, Tuple
from telegram import Bot, ChatMember
from telegram.error import TelegramError
from cachetools import TTLCache
from config import ADMIN_CACHE_TTL, IGNORED_USER_IDS, ACTIVITY_GROUP_ID


# Admin cache: TTLCache ile otomatik temizleme (max 1000 entry, ADMIN_CACHE_TTL süre)
_admin_cache: TTLCache[Tuple[int, int], bool] = TTLCache(maxsize=1000, ttl=ADMIN_CACHE_TTL)


async def is_group_admin(bot: Bot, group_id: int, user_id: int) -> bool:
    """
    Kullanıcının grupta admin olup olmadığını kontrol et

    Args:
        bot: Telegram Bot instance
        group_id: Grup ID
        user_id: Kullanıcı ID

    Returns:
        bool: Admin ise True
    """
    cache_key = (group_id, user_id)

    # Cache'de var mı kontrol et (TTLCache otomatik expire yönetiyor)
    if cache_key in _admin_cache:
        return _admin_cache[cache_key]

    # Telegram API'den kontrol et
    try:
        member = await bot.get_chat_member(group_id, user_id)
        is_admin = member.status in [
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER
        ]

        # Cache'e kaydet (TTLCache otomatik olarak eski kayıtları temizler)
        _admin_cache[cache_key] = is_admin

        return is_admin

    except TelegramError as e:
        print(f"❌ Admin kontrolü hatası: {e}")
        return False


async def is_activity_group_admin(bot: Bot, user_id: int) -> bool:
    """
    Kullanıcının ACTIVITY_GROUP_ID'de admin olup olmadığını kontrol et
    Özelden Randy ayarları için kullanılır

    Args:
        bot: Telegram Bot instance
        user_id: Kullanıcı ID

    Returns:
        bool: Activity group'ta admin ise True
    """
    if not ACTIVITY_GROUP_ID or ACTIVITY_GROUP_ID == 0:
        # ACTIVITY_GROUP_ID ayarlanmamış, herkes ayar yapabilir
        print("⚠️ ACTIVITY_GROUP_ID ayarlanmamış!")
        return True

    return await is_group_admin(bot, ACTIVITY_GROUP_ID, user_id)


async def get_user_admin_groups(bot: Bot, user_id: int, group_ids: list) -> list:
    """
    Kullanıcının admin olduğu grupları döndür

    Args:
        bot: Telegram Bot instance
        user_id: Kullanıcı ID
        group_ids: Kontrol edilecek grup ID'leri

    Returns:
        list: Admin olunan grup ID'leri
    """
    admin_groups = []

    for group_id in group_ids:
        if await is_group_admin(bot, group_id, user_id):
            admin_groups.append(group_id)

    return admin_groups


def is_system_user(user_id: int) -> bool:
    """
    Kullanıcının sistem hesabı olup olmadığını kontrol et
    (Bot mesajları, kanal mesajları, anonim adminler)

    Args:
        user_id: Kullanıcı ID

    Returns:
        bool: Sistem hesabı ise True
    """
    return user_id in IGNORED_USER_IDS


def is_anonymous_admin(message) -> bool:
    """
    Mesajın anonim admin tarafından gönderilip gönderilmediğini kontrol et

    Args:
        message: Telegram Message objesi

    Returns:
        bool: Anonim admin ise True
    """
    # sender_chat varsa ve from.id 1087968824 ise anonim admin
    if message.sender_chat and message.from_user:
        return message.from_user.id == 1087968824
    return False


def can_anonymous_admin_use_commands(message) -> bool:
    """
    Anonim adminin komut kullanıp kullanamayacağını kontrol et
    (Kendi grubundan mesaj gönderiyorsa kullanabilir)

    Args:
        message: Telegram Message objesi

    Returns:
        bool: Komut kullanabilir ise True
    """
    if not is_anonymous_admin(message):
        return False

    # sender_chat.id == chat.id ise aynı gruptan
    if message.sender_chat and message.chat:
        return message.sender_chat.id == message.chat.id

    return False


def clear_admin_cache(group_id: int = None, user_id: int = None):
    """
    Admin cache'ini temizle

    Args:
        group_id: Belirli bir grubun cache'ini temizle (None ise hepsini)
        user_id: Belirli bir kullanıcının cache'ini temizle (None ise hepsini)
    """
    if group_id is None and user_id is None:
        _admin_cache.clear()
        return

    keys_to_remove = []

    for key in list(_admin_cache.keys()):
        g_id, u_id = key
        if (group_id is None or g_id == group_id) and (user_id is None or u_id == user_id):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        _admin_cache.pop(key, None)

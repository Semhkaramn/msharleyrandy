"""
🚫 Etiket Hariç Tutma Servisi
Belirli kullanıcıların etiketlenmesini engeller
- telegram_users tablosundaki is_taggable kolonu kullanılır
- Username girince veritabanından bulunur, API'ye gidilmez
- is_taggable = false olanlar etiketlenmez
"""

from typing import List, Dict, Any, Optional, Tuple
from database import db
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_excluded_users(group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki etiketlenmeyecek kullanıcıları getir (is_taggable = false)

    Args:
        group_id: Grup ID

    Returns:
        List[Dict]: Hariç tutulan kullanıcı listesi
    """
    try:
        async with db.pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, updated_at as created_at
                FROM telegram_users
                WHERE group_id = $1 AND is_taggable = FALSE
                ORDER BY updated_at DESC
            """, group_id)
            return [dict(u) for u in users]
    except Exception as e:
        logger.error(f"Hariç tutulan kullanıcılar getirme hatası: {e}")
        return []


async def get_excluded_user_ids(group_id: int) -> List[int]:
    """
    Gruptaki etiketlenmeyecek kullanıcı ID'lerini getir

    Args:
        group_id: Grup ID

    Returns:
        List[int]: Telegram ID listesi
    """
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT telegram_id FROM telegram_users
                WHERE group_id = $1 AND is_taggable = FALSE
            """, group_id)
            return [row['telegram_id'] for row in rows]
    except Exception as e:
        logger.error(f"Hariç tutulan ID'ler getirme hatası: {e}")
        return []


async def is_user_excluded(group_id: int, telegram_id: int) -> bool:
    """
    Kullanıcı etiketleme listesinden hariç mi?

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID

    Returns:
        bool: Hariç ise True (is_taggable = false)
    """
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT 1 FROM telegram_users
                WHERE group_id = $1 AND telegram_id = $2 AND is_taggable = FALSE
                LIMIT 1
            """, group_id, telegram_id)
            return result is not None
    except Exception as e:
        logger.error(f"Hariç tutma kontrolü hatası: {e}")
        return False


async def find_user_by_username(group_id: int, username: str) -> Optional[Dict[str, Any]]:
    """
    Veritabanından username'e göre kullanıcı bul

    Args:
        group_id: Grup ID
        username: Kullanıcı adı (@ ile veya @ olmadan)

    Returns:
        Dict veya None
    """
    username = username.strip().lstrip('@').lower()

    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT telegram_id, username, first_name, is_taggable
                FROM telegram_users
                WHERE group_id = $1 AND LOWER(username) = $2
                LIMIT 1
            """, group_id, username)
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Kullanıcı arama hatası: {e}")
        return None


async def find_user_by_id(group_id: int, telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Veritabanından telegram_id'ye göre kullanıcı bul

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID

    Returns:
        Dict veya None
    """
    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT telegram_id, username, first_name, is_taggable
                FROM telegram_users
                WHERE group_id = $1 AND telegram_id = $2
                LIMIT 1
            """, group_id, telegram_id)
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Kullanıcı arama hatası: {e}")
        return None


async def set_user_taggable(group_id: int, telegram_id: int, is_taggable: bool) -> Tuple[bool, str]:
    """
    Kullanıcının etiketlenebilirlik durumunu ayarla

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID
        is_taggable: True = etiketlenebilir, False = etiketlenemez

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    try:
        async with db.pool.acquire() as conn:
            # Kullanıcı var mı kontrol et
            user = await conn.fetchrow("""
                SELECT username, first_name, is_taggable
                FROM telegram_users
                WHERE group_id = $1 AND telegram_id = $2
            """, group_id, telegram_id)

            if not user:
                return False, "❌ Bu kullanıcı veritabanında yok. Kullanıcının grupta en az bir mesaj atmış olması gerekiyor."

            current_status = user['is_taggable']
            if current_status is None:
                current_status = True  # Default değer

            if current_status == is_taggable:
                if is_taggable:
                    return False, "Bu kullanıcı zaten etiketlenebilir durumda."
                else:
                    return False, "Bu kullanıcı zaten etiketlenmeyecek listesinde."

            await conn.execute("""
                UPDATE telegram_users
                SET is_taggable = $3, updated_at = NOW()
                WHERE group_id = $1 AND telegram_id = $2
            """, group_id, telegram_id, is_taggable)

            display_name = f"@{user['username']}" if user['username'] else user['first_name'] or str(telegram_id)

            if is_taggable:
                logger.info(f"Etiketlenebilir yapıldı: {display_name} ({telegram_id}) - Grup: {group_id}")
                return True, f"✅ {display_name} artık etiketlenebilir."
            else:
                logger.info(f"Etiket hariç yapıldı: {display_name} ({telegram_id}) - Grup: {group_id}")
                return True, f"✅ {display_name} etiketlenmeyecek listesine eklendi."

    except Exception as e:
        logger.error(f"Etiketlenebilirlik ayarlama hatası: {e}")
        return False, "Bir hata oluştu."


async def add_excluded_user_by_input(group_id: int, user_input: str) -> Tuple[bool, str]:
    """
    Username veya ID ile kullanıcıyı etiketlenmeyecek listesine ekle
    Veritabanından arar, API kullanmaz

    Args:
        group_id: Grup ID
        user_input: @username veya user_id

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    user_input = user_input.strip()

    # Sayı ise ID olarak ara
    if user_input.isdigit():
        telegram_id = int(user_input)
        user = await find_user_by_id(group_id, telegram_id)
        if not user:
            return False, f"❌ ID {telegram_id} veritabanında bulunamadı. Kullanıcının grupta mesaj atmış olması gerekiyor."
        return await set_user_taggable(group_id, telegram_id, False)

    # Username ile ara
    username = user_input.lstrip('@')
    user = await find_user_by_username(group_id, username)

    if not user:
        return False, f"❌ @{username} veritabanında bulunamadı. Kullanıcının grupta mesaj atmış olması gerekiyor."

    return await set_user_taggable(group_id, user['telegram_id'], False)


async def remove_excluded_user(group_id: int, telegram_id: int) -> Tuple[bool, str]:
    """
    Kullanıcıyı etiketlenmeyecek listesinden çıkar (is_taggable = true yap)

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    return await set_user_taggable(group_id, telegram_id, True)


async def remove_excluded_user_by_input(group_id: int, user_input: str) -> Tuple[bool, str]:
    """
    Username veya ID ile kullanıcıyı etiketlenebilir yap

    Args:
        group_id: Grup ID
        user_input: @username veya user_id

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    user_input = user_input.strip()

    # Sayı ise ID olarak ara
    if user_input.isdigit():
        telegram_id = int(user_input)
        return await set_user_taggable(group_id, telegram_id, True)

    # Username ile ara
    username = user_input.lstrip('@')
    user = await find_user_by_username(group_id, username)

    if not user:
        return False, f"❌ @{username} veritabanında bulunamadı."

    return await set_user_taggable(group_id, user['telegram_id'], True)


def format_excluded_users_list(users: List[Dict[str, Any]]) -> str:
    """
    Hariç tutulan kullanıcıları formatla

    Args:
        users: Kullanıcı listesi

    Returns:
        str: Formatlanmış liste
    """
    if not users:
        return "📭 Etiketlenmeyecek kullanıcı yok."

    lines = ["🚫 <b>Etiketlenmeyecek Kullanıcılar:</b>\n"]

    for i, user in enumerate(users, 1):
        telegram_id = user['telegram_id']
        username = user.get('username')
        first_name = user.get('first_name')

        if username:
            display = f"@{username}"
        elif first_name:
            display = first_name
        else:
            display = str(telegram_id)

        lines.append(f"{i}. {display} (ID: <code>{telegram_id}</code>)")

    return "\n".join(lines)


# Eski fonksiyonlar için uyumluluk (eski kod varsa çalışmaya devam etsin)
async def add_excluded_user(
    group_id: int,
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    added_by: int = None
) -> Tuple[bool, str]:
    """
    Eski API uyumluluğu için - set_user_taggable kullanır
    """
    return await set_user_taggable(group_id, telegram_id, False)

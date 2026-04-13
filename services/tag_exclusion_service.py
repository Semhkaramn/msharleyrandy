"""
🚫 Etiket Hariç Tutma Servisi
Belirli kullanıcıların etiketlenmesini engeller
- Username girilse bile telegram_id olarak kaydedilir
- Etiketleme sistemlerinde bu kullanıcılar atlanır
"""

from typing import List, Dict, Any, Optional, Tuple
from database import db
from telegram import Bot
from telegram.error import TelegramError
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_excluded_users(group_id: int) -> List[Dict[str, Any]]:
    """
    Gruptaki etiketlenmeyecek kullanıcıları getir

    Args:
        group_id: Grup ID

    Returns:
        List[Dict]: Hariç tutulan kullanıcı listesi
    """
    try:
        async with db.pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, added_by, created_at
                FROM tag_excluded_users
                WHERE group_id = $1
                ORDER BY created_at DESC
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
                SELECT telegram_id FROM tag_excluded_users WHERE group_id = $1
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
        bool: Hariç ise True
    """
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT 1 FROM tag_excluded_users
                WHERE group_id = $1 AND telegram_id = $2
                LIMIT 1
            """, group_id, telegram_id)
            return result is not None
    except Exception as e:
        logger.error(f"Hariç tutma kontrolü hatası: {e}")
        return False


async def add_excluded_user(
    group_id: int,
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    added_by: int = None
) -> Tuple[bool, str]:
    """
    Kullanıcıyı etiketleme hariç listesine ekle

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID
        username: Kullanıcı adı (opsiyonel)
        first_name: İsim (opsiyonel)
        added_by: Ekleyen admin ID

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    try:
        async with db.pool.acquire() as conn:
            # Zaten var mı kontrol et
            exists = await conn.fetchval("""
                SELECT 1 FROM tag_excluded_users
                WHERE group_id = $1 AND telegram_id = $2
            """, group_id, telegram_id)

            if exists:
                return False, "Bu kullanıcı zaten listede."

            await conn.execute("""
                INSERT INTO tag_excluded_users
                (group_id, telegram_id, username, first_name, added_by)
                VALUES ($1, $2, $3, $4, $5)
            """, group_id, telegram_id, username, first_name, added_by)

            display_name = f"@{username}" if username else first_name or str(telegram_id)
            logger.info(f"Etiket hariç eklendi: {display_name} ({telegram_id}) - Grup: {group_id}")
            return True, f"✅ {display_name} etiketlenmeyecek listesine eklendi."

    except Exception as e:
        logger.error(f"Hariç tutma ekleme hatası: {e}")
        return False, "Bir hata oluştu."


async def remove_excluded_user(group_id: int, telegram_id: int) -> Tuple[bool, str]:
    """
    Kullanıcıyı etiketleme hariç listesinden çıkar

    Args:
        group_id: Grup ID
        telegram_id: Telegram kullanıcı ID

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    try:
        async with db.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM tag_excluded_users
                WHERE group_id = $1 AND telegram_id = $2
            """, group_id, telegram_id)

            if result == "DELETE 0":
                return False, "Bu kullanıcı listede değil."

            logger.info(f"Etiket hariç çıkarıldı: {telegram_id} - Grup: {group_id}")
            return True, f"✅ Kullanıcı etiketlenebilir listesine eklendi."

    except Exception as e:
        logger.error(f"Hariç tutma çıkarma hatası: {e}")
        return False, "Bir hata oluştu."


async def resolve_user_to_id(bot: Bot, user_input: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Kullanıcı girdisini (username veya ID) Telegram ID'ye çevir

    Args:
        bot: Telegram bot instance
        user_input: @username veya user_id

    Returns:
        Tuple[telegram_id, username, first_name] veya (None, None, None) hata durumunda
    """
    user_input = user_input.strip()

    # Sayı ise direkt ID olarak kullan
    if user_input.isdigit():
        telegram_id = int(user_input)
        try:
            # Kullanıcı bilgisini al
            chat = await bot.get_chat(telegram_id)
            return telegram_id, chat.username, chat.first_name
        except TelegramError:
            # ID geçerli ama bilgi alınamadı, yine de kaydet
            return telegram_id, None, None

    # @ ile başlayan username
    username = user_input.lstrip('@')

    try:
        chat = await bot.get_chat(f"@{username}")

        # Kullanıcı mı kontrol et
        if chat.type != 'private':
            return None, None, None

        return chat.id, chat.username, chat.first_name

    except TelegramError as e:
        logger.warning(f"Kullanıcı bulunamadı: {username} - {e}")
        return None, None, None


async def add_excluded_user_by_input(
    bot: Bot,
    group_id: int,
    user_input: str,
    added_by: int
) -> Tuple[bool, str]:
    """
    Username veya ID ile kullanıcıyı hariç listesine ekle

    Args:
        bot: Telegram bot instance
        group_id: Grup ID
        user_input: @username veya user_id
        added_by: Ekleyen admin ID

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    telegram_id, username, first_name = await resolve_user_to_id(bot, user_input)

    if not telegram_id:
        return False, "❌ Kullanıcı bulunamadı. Geçerli bir @username veya user_id girin."

    return await add_excluded_user(
        group_id=group_id,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        added_by=added_by
    )


async def remove_excluded_user_by_input(
    bot: Bot,
    group_id: int,
    user_input: str
) -> Tuple[bool, str]:
    """
    Username veya ID ile kullanıcıyı hariç listesinden çıkar

    Args:
        bot: Telegram bot instance
        group_id: Grup ID
        user_input: @username veya user_id

    Returns:
        Tuple[bool, str]: (Başarılı mı, Mesaj)
    """
    telegram_id, _, _ = await resolve_user_to_id(bot, user_input)

    if not telegram_id:
        return False, "❌ Kullanıcı bulunamadı."

    return await remove_excluded_user(group_id, telegram_id)


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

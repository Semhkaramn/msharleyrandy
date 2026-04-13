"""
🏆 Haftalık Aktivite Ödül Servisi
Haftalık en aktif kullanıcıları belirler ve ödüllendirir
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from database import db
from config import IGNORED_USER_IDS, ACTIVITY_GROUP_ID
from utils.logger import get_logger

# Logger
logger = get_logger(__name__)

# Türkiye saat dilimi
TR_TZ = ZoneInfo("Europe/Istanbul")


async def get_weekly_reward_settings(group_id: int) -> Optional[Dict[str, Any]]:
    """
    Grubun haftalık ödül ayarlarını getir
    """
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow("""
                SELECT * FROM weekly_reward_settings
                WHERE group_id = $1
            """, group_id)

            if settings:
                return dict(settings)
            return None
    except Exception as e:
        logger.error(f"Haftalık ödül ayarları getirme hatası: {e}")
        return None


async def create_or_update_weekly_settings(
    group_id: int,
    enabled: bool = True,
    top_count: int = 5,
    auto_post_sunday: bool = True,
    auto_pin: bool = True,
    post_hour: int = 23,
    post_minute: int = 0
) -> bool:
    """
    Haftalık ödül ayarlarını oluştur veya güncelle
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_reward_settings (
                    group_id, enabled, top_count, auto_post_sunday,
                    auto_pin, post_hour, post_minute, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    enabled = $2, top_count = $3, auto_post_sunday = $4,
                    auto_pin = $5, post_hour = $6, post_minute = $7, updated_at = NOW()
            """, group_id, enabled, top_count, auto_post_sunday, auto_pin, post_hour, post_minute)
            return True
    except Exception as e:
        logger.error(f"Haftalık ödül ayarları kaydetme hatası: {e}")
        return False


async def get_rewards_for_group(group_id: int) -> List[Dict[str, Any]]:
    """
    Grubun tanımlı ödüllerini getir
    """
    try:
        async with db.pool.acquire() as conn:
            rewards = await conn.fetch("""
                SELECT rank, reward_text
                FROM weekly_rewards
                WHERE group_id = $1
                ORDER BY rank ASC
            """, group_id)
            return [dict(r) for r in rewards]
    except Exception as e:
        logger.error(f"Ödüller getirme hatası: {e}")
        return []


async def set_reward(group_id: int, rank: int, reward_text: str) -> bool:
    """
    Belirli bir sıra için ödül ayarla
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_rewards (group_id, rank, reward_text, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (group_id, rank) DO UPDATE SET
                    reward_text = $3, updated_at = NOW()
            """, group_id, rank, reward_text)
            return True
    except Exception as e:
        logger.error(f"Ödül kaydetme hatası: {e}")
        return False


async def delete_reward(group_id: int, rank: int) -> bool:
    """
    Belirli bir sıranın ödülünü sil
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM weekly_rewards
                WHERE group_id = $1 AND rank = $2
            """, group_id, rank)
            return True
    except Exception as e:
        logger.error(f"Ödül silme hatası: {e}")
        return False


async def get_top_active_users(
    group_id: int,
    limit: int = 5,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Haftalık en aktif kullanıcıları getir (adminler hariç)

    Args:
        group_id: Grup ID
        limit: Kaç kişi
        exclude_admin_ids: Hariç tutulacak admin ID'leri
    """
    try:
        async with db.pool.acquire() as conn:
            # Şu anki zamanı al
            now_utc = datetime.now(timezone.utc)
            now_tr = now_utc.astimezone(TR_TZ)

            # Bu haftanın Pazartesi günü 00:00 (Türkiye saati)
            days_since_monday = now_tr.weekday()
            monday_tr = (now_tr - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            period_start = monday_tr.astimezone(timezone.utc).replace(tzinfo=None)

            # Hariç tutulacak ID'ler
            excluded_ids = list(IGNORED_USER_IDS)
            if exclude_admin_ids:
                excluded_ids.extend(exclude_admin_ids)

            # En aktif kullanıcıları getir
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, last_name, weekly_count
                FROM telegram_users
                WHERE group_id = $1
                  AND weekly_count > 0
                  AND last_weekly_reset >= $2
                  AND telegram_id != ALL($3::BIGINT[])
                ORDER BY weekly_count DESC
                LIMIT $4
            """, group_id, period_start, excluded_ids, limit)

            return [dict(u) for u in users]
    except Exception as e:
        logger.error(f"Aktif kullanıcılar getirme hatası: {e}")
        return []


async def get_weekly_leaderboard_with_rewards(
    group_id: int,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Haftalık sıralamayı ödüllerle birlikte getir
    """
    # Ayarları al
    settings = await get_weekly_reward_settings(group_id)
    top_count = settings.get('top_count', 5) if settings else 5

    # En aktif kullanıcıları al
    top_users = await get_top_active_users(group_id, top_count, exclude_admin_ids)

    # Ödülleri al
    rewards = await get_rewards_for_group(group_id)
    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}

    # Birleştir
    result = []
    for i, user in enumerate(top_users, 1):
        user['rank'] = i
        user['reward'] = rewards_dict.get(i, None)
        result.append(user)

    return result


async def save_weekly_history(
    group_id: int,
    leaderboard: List[Dict[str, Any]],
    message_id: int = None
) -> bool:
    """
    Haftalık ödül geçmişini kaydet
    """
    try:
        now_tr = datetime.now(TR_TZ)
        week_number = now_tr.isocalendar()[1]
        year = now_tr.year

        async with db.pool.acquire() as conn:
            for user in leaderboard:
                await conn.execute("""
                    INSERT INTO weekly_reward_history (
                        group_id, week_number, year, rank, telegram_id,
                        username, first_name, message_count, reward_text, message_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (group_id, year, week_number, rank) DO UPDATE SET
                        telegram_id = $5, username = $6, first_name = $7,
                        message_count = $8, reward_text = $9, message_id = $10
                """,
                    group_id, week_number, year, user['rank'], user['telegram_id'],
                    user.get('username'), user.get('first_name'),
                    user.get('weekly_count', 0), user.get('reward'),
                    message_id
                )

            # Ayarlara son paylaşım haftasını kaydet
            await conn.execute("""
                UPDATE weekly_reward_settings
                SET last_posted_week = $1, last_posted_year = $2, updated_at = NOW()
                WHERE group_id = $3
            """, week_number, year, group_id)

            return True
    except Exception as e:
        logger.error(f"Haftalık geçmiş kaydetme hatası: {e}")
        return False


async def has_posted_this_week(group_id: int) -> bool:
    """
    Bu hafta zaten paylaşım yapılmış mı?
    """
    try:
        now_tr = datetime.now(TR_TZ)
        week_number = now_tr.isocalendar()[1]
        year = now_tr.year

        settings = await get_weekly_reward_settings(group_id)
        if not settings:
            return False

        return (
            settings.get('last_posted_week') == week_number and
            settings.get('last_posted_year') == year
        )
    except Exception as e:
        logger.error(f"Haftalık kontrol hatası: {e}")
        return False


async def get_group_admin_ids(bot, group_id: int) -> List[int]:
    """
    Grubun admin ID'lerini getir
    """
    try:
        admins = await bot.get_chat_administrators(group_id)
        return [admin.user.id for admin in admins if not admin.user.is_bot]
    except Exception as e:
        logger.error(f"Admin listesi alma hatası: {e}")
        return []


async def toggle_weekly_rewards(group_id: int, enabled: bool) -> bool:
    """
    Haftalık ödül sistemini aç/kapa
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_reward_settings (group_id, enabled, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    enabled = $2, updated_at = NOW()
            """, group_id, enabled)
            return True
    except Exception as e:
        logger.error(f"Haftalık ödül toggle hatası: {e}")
        return False


async def update_auto_pin(group_id: int, auto_pin: bool) -> bool:
    """
    Otomatik sabitlemeyi aç/kapa
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_reward_settings (group_id, auto_pin, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    auto_pin = $2, updated_at = NOW()
            """, group_id, auto_pin)
            return True
    except Exception as e:
        logger.error(f"Auto pin güncelleme hatası: {e}")
        return False


async def update_post_time(group_id: int, hour: int, minute: int = 0) -> bool:
    """
    Paylaşım saatini güncelle
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_reward_settings (group_id, post_hour, post_minute, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    post_hour = $2, post_minute = $3, updated_at = NOW()
            """, group_id, hour, minute)
            return True
    except Exception as e:
        logger.error(f"Paylaşım saati güncelleme hatası: {e}")
        return False


async def update_top_count(group_id: int, count: int) -> bool:
    """
    Kaç kişinin gösterileceğini güncelle
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO weekly_reward_settings (group_id, top_count, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    top_count = $2, updated_at = NOW()
            """, group_id, count)
            return True
    except Exception as e:
        logger.error(f"Top count güncelleme hatası: {e}")
        return False

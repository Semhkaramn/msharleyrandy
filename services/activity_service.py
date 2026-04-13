"""
🏆 Aktivite Ödül Servisi
Günlük, Haftalık, Aylık aktivite takibi ve ödül sistemi
Manuel başlat/durdur sistemi - .aktiflik komutu için
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

logger = get_logger(__name__)

# Türkiye saat dilimi
TR_TZ = ZoneInfo("Europe/Istanbul")

# Aktivite tipleri
ACTIVITY_TYPES = {
    'daily': 'Günlük',
    'weekly': 'Haftalık',
    'monthly': 'Aylık'
}


async def ensure_activity_tables():
    """Aktivite tablolarını oluştur (migration)"""
    try:
        async with db.pool.acquire() as conn:
            # Aktivite ayarları tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_settings (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    activity_type TEXT DEFAULT 'weekly',
                    enabled BOOLEAN DEFAULT FALSE,
                    top_count INT DEFAULT 20,
                    auto_reset BOOLEAN DEFAULT TRUE,
                    auto_post BOOLEAN DEFAULT FALSE,
                    auto_pin BOOLEAN DEFAULT TRUE,
                    post_hour INT DEFAULT 23,
                    post_minute INT DEFAULT 0,
                    last_reset_at TIMESTAMP,
                    last_posted_at TIMESTAMP,
                    started_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Aktivite ödülleri tablosu (periyod bazlı)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_rewards (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    rank INT NOT NULL,
                    reward_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, rank)
                )
            """)

            # İndeksler
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_settings_group ON activity_settings(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_rewards_group ON activity_rewards(group_id)")

            return True
    except Exception as e:
        logger.error(f"❌ Aktivite tabloları oluşturma hatası: {e}")
        return False


async def get_activity_settings(group_id: int) -> Optional[Dict[str, Any]]:
    """Grubun aktivite ayarlarını getir"""
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow("""
                SELECT * FROM activity_settings
                WHERE group_id = $1
            """, group_id)

            if settings:
                return dict(settings)
            return None
    except Exception as e:
        logger.error(f"❌ Aktivite ayarları getirme hatası: {e}")
        return None


async def create_or_update_activity_settings(
    group_id: int,
    activity_type: str = None,
    enabled: bool = None,
    top_count: int = None,
    auto_reset: bool = None,
    auto_post: bool = None,
    auto_pin: bool = None,
    post_hour: int = None,
    post_minute: int = None,
    started_at: datetime = None
) -> bool:
    """Aktivite ayarlarını oluştur veya güncelle"""
    try:
        async with db.pool.acquire() as conn:
            # Mevcut ayarları al
            existing = await get_activity_settings(group_id)

            if existing:
                # Güncelle
                updates = []
                values = []
                idx = 1

                if activity_type is not None:
                    updates.append(f"activity_type = ${idx}")
                    values.append(activity_type)
                    idx += 1

                if enabled is not None:
                    updates.append(f"enabled = ${idx}")
                    values.append(enabled)
                    idx += 1

                if top_count is not None:
                    updates.append(f"top_count = ${idx}")
                    values.append(top_count)
                    idx += 1

                if auto_reset is not None:
                    updates.append(f"auto_reset = ${idx}")
                    values.append(auto_reset)
                    idx += 1

                if auto_post is not None:
                    updates.append(f"auto_post = ${idx}")
                    values.append(auto_post)
                    idx += 1

                if auto_pin is not None:
                    updates.append(f"auto_pin = ${idx}")
                    values.append(auto_pin)
                    idx += 1

                if post_hour is not None:
                    updates.append(f"post_hour = ${idx}")
                    values.append(post_hour)
                    idx += 1

                if post_minute is not None:
                    updates.append(f"post_minute = ${idx}")
                    values.append(post_minute)
                    idx += 1

                if started_at is not None:
                    updates.append(f"started_at = ${idx}")
                    values.append(started_at)
                    idx += 1

                if updates:
                    updates.append("updated_at = NOW()")
                    values.append(group_id)

                    query = f"""
                        UPDATE activity_settings
                        SET {', '.join(updates)}
                        WHERE group_id = ${idx}
                    """
                    await conn.execute(query, *values)
            else:
                # Yeni oluştur
                await conn.execute("""
                    INSERT INTO activity_settings (
                        group_id, activity_type, enabled, top_count,
                        auto_reset, auto_post, auto_pin, post_hour, post_minute,
                        started_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    group_id,
                    activity_type or 'weekly',
                    enabled if enabled is not None else False,
                    top_count or 20,
                    auto_reset if auto_reset is not None else False,
                    auto_post if auto_post is not None else False,
                    auto_pin if auto_pin is not None else True,
                    post_hour or 23,
                    post_minute or 0,
                    started_at
                )

            return True
    except Exception as e:
        logger.error(f"❌ Aktivite ayarları kaydetme hatası: {e}")
        return False


async def set_activity_type(group_id: int, activity_type: str) -> bool:
    """Aktivite tipini ayarla (daily/weekly/monthly)"""
    if activity_type not in ACTIVITY_TYPES:
        return False
    return await create_or_update_activity_settings(group_id, activity_type=activity_type)


async def toggle_activity(group_id: int, enabled: bool) -> bool:
    """Aktivite sistemini aç/kapa"""
    return await create_or_update_activity_settings(group_id, enabled=enabled)


async def get_activity_rewards(group_id: int, activity_type: str = None) -> List[Dict[str, Any]]:
    """Aktivite ödüllerini getir"""
    try:
        async with db.pool.acquire() as conn:
            rewards = await conn.fetch("""
                SELECT rank, reward_text
                FROM activity_rewards
                WHERE group_id = $1
                ORDER BY rank ASC
            """, group_id)

            return [dict(r) for r in rewards]
    except Exception as e:
        logger.error(f"❌ Aktivite ödülleri getirme hatası: {e}")
        return []


async def set_activity_reward(group_id: int, rank: int, reward_text: str) -> bool:
    """Tek bir ödül ayarla"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO activity_rewards (group_id, rank, reward_text, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (group_id, rank) DO UPDATE SET
                    reward_text = $3, updated_at = NOW()
            """, group_id, rank, reward_text)
            return True
    except Exception as e:
        logger.error(f"❌ Ödül kaydetme hatası: {e}")
        return False


async def delete_activity_reward(group_id: int, rank: int) -> bool:
    """Ödülü sil"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM activity_rewards
                WHERE group_id = $1 AND rank = $2
            """, group_id, rank)
            return True
    except Exception as e:
        logger.error(f"❌ Ödül silme hatası: {e}")
        return False


async def get_activity_leaderboard(
    group_id: int,
    activity_type: str = None,
    limit: int = 20,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Aktivite sıralamasını getir
    BAĞIMSIZ activity_count alanını kullanır
    enabled olup olmadığına bakmaz - her zaman mevcut veriyi döner
    """
    try:
        # Ayarları al
        settings = await get_activity_settings(group_id)

        # Hariç tutulacak ID'ler
        excluded_ids = list(IGNORED_USER_IDS)
        if exclude_admin_ids:
            excluded_ids.extend(exclude_admin_ids)

        async with db.pool.acquire() as conn:
            # BAĞIMSIZ activity_count alanını kullan
            if excluded_ids:
                users = await conn.fetch("""
                    SELECT telegram_id, username, first_name, last_name, activity_count as message_count
                    FROM telegram_users
                    WHERE group_id = $1
                      AND activity_count > 0
                      AND telegram_id != ALL($2::BIGINT[])
                    ORDER BY activity_count DESC
                    LIMIT $3
                """, group_id, excluded_ids, limit)
            else:
                users = await conn.fetch("""
                    SELECT telegram_id, username, first_name, last_name, activity_count as message_count
                    FROM telegram_users
                    WHERE group_id = $1
                      AND activity_count > 0
                    ORDER BY activity_count DESC
                    LIMIT $2
                """, group_id, limit)

            return [dict(u) for u in users]
    except Exception as e:
        logger.error(f"❌ Aktivite sıralaması getirme hatası: {e}")
        return []


async def get_leaderboard_with_rewards(
    group_id: int,
    activity_type: str = None,
    exclude_admin_ids: List[int] = None,
    limit: int = None
) -> List[Dict[str, Any]]:
    """Sıralamayı ödüllerle birlikte getir

    Args:
        limit: Gösterilecek kişi sayısı. None ise settings'den alınır.
    """
    settings = await get_activity_settings(group_id)

    if not activity_type:
        if settings:
            activity_type = settings.get('activity_type', 'weekly')
        else:
            activity_type = 'weekly'

    # Limit belirtilmişse onu kullan, değilse settings'den al
    if limit is not None:
        top_count = limit
    else:
        top_count = settings.get('top_count', 20) if settings else 20

    # Sıralamayı al
    users = await get_activity_leaderboard(group_id, activity_type, top_count, exclude_admin_ids)

    # Ödülleri al
    rewards = await get_activity_rewards(group_id)
    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}

    # Birleştir
    result = []
    for i, user in enumerate(users, 1):
        user['rank'] = i
        user['reward'] = rewards_dict.get(i)
        result.append(user)

    return result


async def get_user_activity_rank(user_id: int, group_id: int, activity_type: str = None) -> int:
    """Kullanıcının aktivite sıralamasındaki yerini getir"""
    try:
        async with db.pool.acquire() as conn:
            # Kullanıcının mesaj sayısını al
            user_count = await conn.fetchval("""
                SELECT activity_count FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2
            """, user_id, group_id)

            if not user_count:
                return 0

            # Kaç kişi önde
            rank = await conn.fetchval("""
                SELECT COUNT(*) + 1 FROM telegram_users
                WHERE group_id = $1 AND activity_count > $2
            """, group_id, user_count)

            return rank or 0
    except Exception as e:
        logger.error(f"❌ Kullanıcı sıralama hatası: {e}")
        return 0


def get_activity_type_text(activity_type: str) -> str:
    """Aktivite tipi metnini döndür"""
    return ACTIVITY_TYPES.get(activity_type, activity_type)


def get_period_info(activity_type: str) -> str:
    """Periyot bilgisini döndür"""
    now = datetime.now(TR_TZ)

    if activity_type == 'daily':
        return now.strftime('%d %B %Y')
    elif activity_type == 'weekly':
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        return f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"
    elif activity_type == 'monthly':
        return now.strftime('%B %Y')

    return ""


def get_next_reset_time(activity_type: str) -> str:
    """Bir sonraki sıfırlama zamanını döndür"""
    now = datetime.now(TR_TZ)

    if activity_type == 'daily':
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_reset.strftime('%d.%m.%Y %H:%M')
    elif activity_type == 'weekly':
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_reset = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_reset.strftime('%d.%m.%Y %H:%M')
    elif activity_type == 'monthly':
        if now.month == 12:
            next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return next_reset.strftime('%d.%m.%Y %H:%M')

    return ""


async def start_activity_tracking(group_id: int, activity_type: str = 'weekly') -> bool:
    """
    Aktivite takibini başlat
    - Tüm kullanıcıların activity_count'unu sıfırla
    - Başlama tarihini kaydet
    - enabled = True yap
    """
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with db.pool.acquire() as conn:
            # Tüm kullanıcıların activity_count'unu sıfırla
            await conn.execute("""
                UPDATE telegram_users
                SET activity_count = 0, activity_last_reset = $1
                WHERE group_id = $2
            """, now, group_id)

        # Ayarları güncelle
        return await create_or_update_activity_settings(
            group_id,
            activity_type=activity_type,
            enabled=True,
            started_at=now
        )
    except Exception as e:
        logger.error(f"❌ Aktivite takibi başlatma hatası: {e}")
        return False


async def stop_activity_tracking(group_id: int) -> bool:
    """
    Aktivite takibini durdur
    - Sadece enabled = False yap
    - Veriler silinmez, son sıralama görüntülenebilir
    """
    try:
        return await create_or_update_activity_settings(
            group_id,
            enabled=False
        )
    except Exception as e:
        logger.error(f"❌ Aktivite takibi durdurma hatası: {e}")
        return False


async def get_activity_status(group_id: int) -> Dict[str, Any]:
    """
    Aktivite durumunu detaylı getir
    - enabled: Aktif mi?
    - started_at: Ne zaman başladı?
    - activity_type: Periyod tipi
    - has_data: Veri var mı?
    """
    try:
        settings = await get_activity_settings(group_id)

        # Veri var mı kontrol et
        async with db.pool.acquire() as conn:
            has_data = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM telegram_users
                    WHERE group_id = $1 AND activity_count > 0
                )
            """, group_id)

        if settings:
            return {
                'enabled': settings.get('enabled', False),
                'started_at': settings.get('started_at'),
                'activity_type': settings.get('activity_type', 'weekly'),
                'top_count': settings.get('top_count', 20),
                'has_data': has_data
            }

        return {
            'enabled': False,
            'started_at': None,
            'activity_type': 'weekly',
            'top_count': 20,
            'has_data': has_data
        }
    except Exception as e:
        logger.error(f"❌ Aktivite durumu getirme hatası: {e}")
        return {
            'enabled': False,
            'started_at': None,
            'activity_type': 'weekly',
            'top_count': 20,
            'has_data': False
        }

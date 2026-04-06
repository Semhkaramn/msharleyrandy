"""
🏆 Aktivite Ödül Servisi
Günlük, Haftalık, Aylık aktivite takibi ve ödül sistemi
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from database import db
from config import IGNORED_USER_IDS, ACTIVITY_GROUP_ID

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
                    started_at TIMESTAMP,
                    period_start_day INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Aktivite ödülleri tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_rewards (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    activity_type TEXT NOT NULL,
                    rank INT NOT NULL,
                    reward_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, activity_type, rank)
                )
            """)

            # Aktivite mesaj sayacı tablosu (period bazlı)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_counts (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    activity_type TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    message_count INT DEFAULT 0,
                    started_at TIMESTAMP NOT NULL,
                    last_message_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, telegram_id, activity_type, period_key)
                )
            """)

            # İndeksler
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_counts_group ON activity_counts(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_counts_type ON activity_counts(activity_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_counts_period ON activity_counts(period_key)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_settings_group ON activity_settings(group_id)")

            return True
    except Exception as e:
        print(f"❌ Aktivite tabloları oluşturma hatası: {e}")
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
        print(f"❌ Aktivite ayarları getirme hatası: {e}")
        return None


async def create_or_update_activity_settings(
    group_id: int,
    activity_type: str = None,
    enabled: bool = None,
    top_count: int = None,
    period_start_day: int = None
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

                if period_start_day is not None:
                    updates.append(f"period_start_day = ${idx}")
                    values.append(period_start_day)
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
                        group_id, activity_type, enabled, top_count, period_start_day, started_at
                    ) VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                    group_id,
                    activity_type or 'weekly',
                    enabled if enabled is not None else False,
                    top_count or 20,
                    period_start_day or 1
                )

            return True
    except Exception as e:
        print(f"❌ Aktivite ayarları kaydetme hatası: {e}")
        return False


async def start_activity_tracking(group_id: int, activity_type: str) -> bool:
    """Aktivite takibini başlat"""
    try:
        async with db.pool.acquire() as conn:
            now = datetime.now(TR_TZ)

            # Ayarları güncelle
            await conn.execute("""
                INSERT INTO activity_settings (group_id, activity_type, enabled, started_at, updated_at)
                VALUES ($1, $2, TRUE, $3, NOW())
                ON CONFLICT (group_id) DO UPDATE SET
                    activity_type = $2, enabled = TRUE, started_at = $3, updated_at = NOW()
            """, group_id, activity_type, now)

            return True
    except Exception as e:
        print(f"❌ Aktivite başlatma hatası: {e}")
        return False


async def stop_activity_tracking(group_id: int) -> bool:
    """Aktivite takibini durdur"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE activity_settings
                SET enabled = FALSE, updated_at = NOW()
                WHERE group_id = $1
            """, group_id)
            return True
    except Exception as e:
        print(f"❌ Aktivite durdurma hatası: {e}")
        return False


def get_period_key(activity_type: str, start_date: datetime = None) -> str:
    """Periyot anahtarı oluştur"""
    now = datetime.now(TR_TZ)

    if activity_type == 'daily':
        return now.strftime('%Y-%m-%d')
    elif activity_type == 'weekly':
        # Haftanın başlangıcı (Pazartesi)
        week_start = now - timedelta(days=now.weekday())
        return week_start.strftime('%Y-W%W')
    elif activity_type == 'monthly':
        return now.strftime('%Y-%m')

    return now.strftime('%Y-%m-%d')


async def track_activity_message(
    group_id: int,
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None
) -> bool:
    """Aktivite mesajını say"""
    try:
        # Ayarları kontrol et
        settings = await get_activity_settings(group_id)

        if not settings or not settings.get('enabled'):
            return False

        activity_type = settings.get('activity_type', 'weekly')
        period_key = get_period_key(activity_type)
        started_at = settings.get('started_at') or datetime.now(TR_TZ)

        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO activity_counts (
                    group_id, telegram_id, username, first_name, last_name,
                    activity_type, period_key, message_count, started_at, last_message_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 1, $8, NOW())
                ON CONFLICT (group_id, telegram_id, activity_type, period_key) DO UPDATE SET
                    username = COALESCE($3, activity_counts.username),
                    first_name = COALESCE($4, activity_counts.first_name),
                    last_name = COALESCE($5, activity_counts.last_name),
                    message_count = activity_counts.message_count + 1,
                    last_message_at = NOW(),
                    updated_at = NOW()
            """, group_id, user_id, username, first_name, last_name,
                activity_type, period_key, started_at)

            return True
    except Exception as e:
        print(f"❌ Aktivite mesaj sayma hatası: {e}")
        return False


async def get_activity_leaderboard(
    group_id: int,
    activity_type: str = None,
    limit: int = 20,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """Aktivite sıralamasını getir"""
    try:
        # Ayarları al
        settings = await get_activity_settings(group_id)

        if not activity_type and settings:
            activity_type = settings.get('activity_type', 'weekly')
        elif not activity_type:
            activity_type = 'weekly'

        period_key = get_period_key(activity_type)

        # Hariç tutulacak ID'ler
        excluded_ids = list(IGNORED_USER_IDS)
        if exclude_admin_ids:
            excluded_ids.extend(exclude_admin_ids)

        async with db.pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT telegram_id, username, first_name, last_name, message_count
                FROM activity_counts
                WHERE group_id = $1
                  AND activity_type = $2
                  AND period_key = $3
                  AND message_count > 0
                  AND telegram_id != ALL($4::BIGINT[])
                ORDER BY message_count DESC
                LIMIT $5
            """, group_id, activity_type, period_key, excluded_ids, limit)

            return [dict(u) for u in users]
    except Exception as e:
        print(f"❌ Aktivite sıralaması getirme hatası: {e}")
        return []


async def get_activity_rewards(group_id: int, activity_type: str = None) -> List[Dict[str, Any]]:
    """Aktivite ödüllerini getir"""
    try:
        settings = await get_activity_settings(group_id)

        if not activity_type and settings:
            activity_type = settings.get('activity_type', 'weekly')
        elif not activity_type:
            activity_type = 'weekly'

        async with db.pool.acquire() as conn:
            rewards = await conn.fetch("""
                SELECT rank, reward_text
                FROM activity_rewards
                WHERE group_id = $1 AND activity_type = $2
                ORDER BY rank ASC
            """, group_id, activity_type)

            return [dict(r) for r in rewards]
    except Exception as e:
        print(f"❌ Aktivite ödülleri getirme hatası: {e}")
        return []


async def set_activity_rewards(group_id: int, activity_type: str, rewards_text: str) -> bool:
    """
    Aktivite ödüllerini toplu ayarla
    rewards_text: Satır satır ödüller (1. satır = 1. sıra)
    """
    try:
        lines = [line.strip() for line in rewards_text.strip().split('\n') if line.strip()]

        async with db.pool.acquire() as conn:
            # Önce mevcut ödülleri sil
            await conn.execute("""
                DELETE FROM activity_rewards
                WHERE group_id = $1 AND activity_type = $2
            """, group_id, activity_type)

            # Yeni ödülleri ekle
            for rank, reward in enumerate(lines, 1):
                await conn.execute("""
                    INSERT INTO activity_rewards (group_id, activity_type, rank, reward_text)
                    VALUES ($1, $2, $3, $4)
                """, group_id, activity_type, rank, reward)

            return True
    except Exception as e:
        print(f"❌ Aktivite ödülleri kaydetme hatası: {e}")
        return False


async def set_single_reward(group_id: int, activity_type: str, rank: int, reward_text: str) -> bool:
    """Tek bir ödül ayarla"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO activity_rewards (group_id, activity_type, rank, reward_text, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (group_id, activity_type, rank) DO UPDATE SET
                    reward_text = $4, updated_at = NOW()
            """, group_id, activity_type, rank, reward_text)
            return True
    except Exception as e:
        print(f"❌ Ödül kaydetme hatası: {e}")
        return False


async def get_leaderboard_with_rewards(
    group_id: int,
    activity_type: str = None,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """Sıralamayı ödüllerle birlikte getir"""
    settings = await get_activity_settings(group_id)

    if not activity_type and settings:
        activity_type = settings.get('activity_type', 'weekly')
    elif not activity_type:
        activity_type = 'weekly'

    top_count = settings.get('top_count', 20) if settings else 20

    # Sıralamayı al
    users = await get_activity_leaderboard(group_id, activity_type, top_count, exclude_admin_ids)

    # Ödülleri al
    rewards = await get_activity_rewards(group_id, activity_type)
    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}

    # Birleştir
    result = []
    for i, user in enumerate(users, 1):
        user['rank'] = i
        user['reward'] = rewards_dict.get(i)
        result.append(user)

    return result


async def get_user_activity_stats(user_id: int, group_id: int) -> Dict[str, int]:
    """Kullanıcının aktivite istatistiklerini getir"""
    try:
        now = datetime.now(TR_TZ)

        async with db.pool.acquire() as conn:
            # Günlük
            daily_key = get_period_key('daily')
            daily = await conn.fetchval("""
                SELECT message_count FROM activity_counts
                WHERE group_id = $1 AND telegram_id = $2
                AND activity_type = 'daily' AND period_key = $3
            """, group_id, user_id, daily_key) or 0

            # Haftalık
            weekly_key = get_period_key('weekly')
            weekly = await conn.fetchval("""
                SELECT message_count FROM activity_counts
                WHERE group_id = $1 AND telegram_id = $2
                AND activity_type = 'weekly' AND period_key = $3
            """, group_id, user_id, weekly_key) or 0

            # Aylık
            monthly_key = get_period_key('monthly')
            monthly = await conn.fetchval("""
                SELECT message_count FROM activity_counts
                WHERE group_id = $1 AND telegram_id = $2
                AND activity_type = 'monthly' AND period_key = $3
            """, group_id, user_id, monthly_key) or 0

            return {
                'daily': daily,
                'weekly': weekly,
                'monthly': monthly
            }
    except Exception as e:
        print(f"❌ Kullanıcı aktivite istatistikleri hatası: {e}")
        return {'daily': 0, 'weekly': 0, 'monthly': 0}


async def reset_activity_counts(group_id: int, activity_type: str = None) -> bool:
    """Aktivite sayaçlarını sıfırla (sadece adminler)"""
    try:
        async with db.pool.acquire() as conn:
            if activity_type:
                period_key = get_period_key(activity_type)
                await conn.execute("""
                    DELETE FROM activity_counts
                    WHERE group_id = $1 AND activity_type = $2 AND period_key = $3
                """, group_id, activity_type, period_key)
            else:
                await conn.execute("""
                    DELETE FROM activity_counts
                    WHERE group_id = $1
                """, group_id)

            return True
    except Exception as e:
        print(f"❌ Aktivite sıfırlama hatası: {e}")
        return False


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

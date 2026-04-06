"""
🏆 Aktivite Ödül Servisi
Günlük, Haftalık, Aylık aktivite takibi ve ödül sistemi
Periyod sonunda otomatik sıfırlama
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
    auto_reset: bool = None,
    auto_post: bool = None,
    auto_pin: bool = None,
    post_hour: int = None,
    post_minute: int = None
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
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """,
                    group_id,
                    activity_type or 'weekly',
                    enabled if enabled is not None else True,
                    top_count or 20,
                    auto_reset if auto_reset is not None else True,
                    auto_post if auto_post is not None else False,
                    auto_pin if auto_pin is not None else True,
                    post_hour or 23,
                    post_minute or 0
                )

            return True
    except Exception as e:
        print(f"❌ Aktivite ayarları kaydetme hatası: {e}")
        return False


async def set_activity_type(group_id: int, activity_type: str) -> bool:
    """Aktivite tipini ayarla (daily/weekly/monthly)"""
    if activity_type not in ACTIVITY_TYPES:
        return False
    return await create_or_update_activity_settings(group_id, activity_type=activity_type, enabled=True)


async def toggle_activity(group_id: int, enabled: bool) -> bool:
    """Aktivite sistemini aç/kapa"""
    return await create_or_update_activity_settings(group_id, enabled=enabled)


async def get_activity_rewards(group_id: int) -> List[Dict[str, Any]]:
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
        print(f"❌ Aktivite ödülleri getirme hatası: {e}")
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
        print(f"❌ Ödül kaydetme hatası: {e}")
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
        print(f"❌ Ödül silme hatası: {e}")
        return False


async def get_activity_leaderboard(
    group_id: int,
    activity_type: str = None,
    limit: int = 20,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Aktivite sıralamasını getir
    telegram_users tablosundan daily_count, weekly_count, monthly_count kullanır
    """
    try:
        # Ayarları al
        settings = await get_activity_settings(group_id)

        if not activity_type:
            if settings:
                activity_type = settings.get('activity_type', 'weekly')
            else:
                activity_type = 'weekly'

        # Hariç tutulacak ID'ler
        excluded_ids = list(IGNORED_USER_IDS)
        if exclude_admin_ids:
            excluded_ids.extend(exclude_admin_ids)

        # Periyod başlangıcını hesapla
        now_utc = datetime.now(timezone.utc)
        now_tr = now_utc.astimezone(TR_TZ)

        if activity_type == 'daily':
            field = 'daily_count'
            reset_field = 'last_daily_reset'
            # Bugünün başlangıcı (Türkiye saati 00:00)
            period_start_tr = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
        elif activity_type == 'weekly':
            field = 'weekly_count'
            reset_field = 'last_weekly_reset'
            # Bu haftanın Pazartesi günü 00:00
            days_since_monday = now_tr.weekday()
            period_start_tr = (now_tr - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:  # monthly
            field = 'monthly_count'
            reset_field = 'last_monthly_reset'
            # Bu ayın 1'i 00:00
            period_start_tr = now_tr.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        period_start = period_start_tr.astimezone(timezone.utc).replace(tzinfo=None)

        async with db.pool.acquire() as conn:
            if excluded_ids:
                users = await conn.fetch(f"""
                    SELECT telegram_id, username, first_name, last_name, {field} as message_count
                    FROM telegram_users
                    WHERE group_id = $1
                      AND {field} > 0
                      AND {reset_field} >= $2
                      AND telegram_id != ALL($3::BIGINT[])
                    ORDER BY {field} DESC
                    LIMIT $4
                """, group_id, period_start, excluded_ids, limit)
            else:
                users = await conn.fetch(f"""
                    SELECT telegram_id, username, first_name, last_name, {field} as message_count
                    FROM telegram_users
                    WHERE group_id = $1
                      AND {field} > 0
                      AND {reset_field} >= $2
                    ORDER BY {field} DESC
                    LIMIT $3
                """, group_id, period_start, limit)

            return [dict(u) for u in users]
    except Exception as e:
        print(f"❌ Aktivite sıralaması getirme hatası: {e}")
        return []


async def get_leaderboard_with_rewards(
    group_id: int,
    activity_type: str = None,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """Sıralamayı ödüllerle birlikte getir"""
    settings = await get_activity_settings(group_id)

    if not activity_type:
        if settings:
            activity_type = settings.get('activity_type', 'weekly')
        else:
            activity_type = 'weekly'

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
        settings = await get_activity_settings(group_id)

        if not activity_type:
            if settings:
                activity_type = settings.get('activity_type', 'weekly')
            else:
                activity_type = 'weekly'

        # Periyod başlangıcını hesapla
        now_utc = datetime.now(timezone.utc)
        now_tr = now_utc.astimezone(TR_TZ)

        if activity_type == 'daily':
            field = 'daily_count'
            reset_field = 'last_daily_reset'
            period_start_tr = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
        elif activity_type == 'weekly':
            field = 'weekly_count'
            reset_field = 'last_weekly_reset'
            days_since_monday = now_tr.weekday()
            period_start_tr = (now_tr - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            field = 'monthly_count'
            reset_field = 'last_monthly_reset'
            period_start_tr = now_tr.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        period_start = period_start_tr.astimezone(timezone.utc).replace(tzinfo=None)

        async with db.pool.acquire() as conn:
            # Kullanıcının mesaj sayısını al
            user_count = await conn.fetchval(f"""
                SELECT {field} FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2 AND {reset_field} >= $3
            """, user_id, group_id, period_start)

            if not user_count:
                return 0

            # Kaç kişi önde
            rank = await conn.fetchval(f"""
                SELECT COUNT(*) + 1 FROM telegram_users
                WHERE group_id = $1 AND {field} > $2 AND {reset_field} >= $3
            """, group_id, user_count, period_start)

            return rank or 0
    except Exception as e:
        print(f"❌ Kullanıcı sıralama hatası: {e}")
        return 0


async def check_and_reset_period(group_id: int) -> bool:
    """
    Periyod kontrolü yap ve gerekirse sıfırla
    Bu fonksiyon scheduler tarafından çağrılır
    """
    try:
        settings = await get_activity_settings(group_id)
        if not settings or not settings.get('enabled') or not settings.get('auto_reset'):
            return False

        activity_type = settings.get('activity_type', 'weekly')
        last_reset = settings.get('last_reset_at')

        now_utc = datetime.now(timezone.utc)
        now_tr = now_utc.astimezone(TR_TZ)

        should_reset = False

        if activity_type == 'daily':
            # Her gün gece yarısı
            if not last_reset:
                should_reset = True
            else:
                last_reset_tr = last_reset.astimezone(TR_TZ) if last_reset.tzinfo else last_reset.replace(tzinfo=timezone.utc).astimezone(TR_TZ)
                should_reset = last_reset_tr.date() < now_tr.date()

        elif activity_type == 'weekly':
            # Her Pazartesi gece yarısı
            if not last_reset:
                should_reset = True
            else:
                last_reset_tr = last_reset.astimezone(TR_TZ) if last_reset.tzinfo else last_reset.replace(tzinfo=timezone.utc).astimezone(TR_TZ)
                last_monday = last_reset_tr.date() - timedelta(days=last_reset_tr.weekday())
                current_monday = now_tr.date() - timedelta(days=now_tr.weekday())
                should_reset = last_monday < current_monday

        elif activity_type == 'monthly':
            # Her ayın 1'i gece yarısı
            if not last_reset:
                should_reset = True
            else:
                last_reset_tr = last_reset.astimezone(TR_TZ) if last_reset.tzinfo else last_reset.replace(tzinfo=timezone.utc).astimezone(TR_TZ)
                should_reset = (last_reset_tr.year, last_reset_tr.month) < (now_tr.year, now_tr.month)

        if should_reset:
            # Sıfırlama zamanını güncelle
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE activity_settings
                    SET last_reset_at = NOW(), updated_at = NOW()
                    WHERE group_id = $1
                """, group_id)

            return True

        return False
    except Exception as e:
        print(f"❌ Periyod sıfırlama kontrolü hatası: {e}")
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

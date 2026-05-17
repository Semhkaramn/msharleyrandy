"""
🏆 Aktivite Ödül Servisi
Manuel başlat/durdur sistemi - .aktiflik komutu için
Minimum karakter kuralı ile mesaj sayımı
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


async def ensure_activity_tables():
    """Aktivite tablolarını oluştur (migration)"""
    try:
        async with db.pool.acquire() as conn:
            # Aktivite ayarları tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_settings (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    top_count INT DEFAULT 20,
                    min_char_count INT DEFAULT 10,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # min_char_count ve ended_at kolonları yoksa ekle (migration)
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name='activity_settings' AND column_name='min_char_count') THEN
                        ALTER TABLE activity_settings ADD COLUMN min_char_count INT DEFAULT 10;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name='activity_settings' AND column_name='ended_at') THEN
                        ALTER TABLE activity_settings ADD COLUMN ended_at TIMESTAMP;
                    END IF;
                END $$;
            """)

            # Aktivite ödülleri tablosu
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


async def get_min_char_count(group_id: int) -> int:
    """Grubun minimum karakter sayısı ayarını getir"""
    try:
        settings = await get_activity_settings(group_id)
        if settings:
            return settings.get('min_char_count', 10) or 10
        return 10
    except Exception as e:
        logger.error(f"❌ Min char count getirme hatası: {e}")
        return 10


async def create_or_update_activity_settings(
    group_id: int,
    enabled: bool = None,
    top_count: int = None,
    min_char_count: int = None,
    started_at: datetime = None,
    ended_at: datetime = None
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

                if enabled is not None:
                    updates.append(f"enabled = ${idx}")
                    values.append(enabled)
                    idx += 1

                if top_count is not None:
                    updates.append(f"top_count = ${idx}")
                    values.append(top_count)
                    idx += 1

                if min_char_count is not None:
                    updates.append(f"min_char_count = ${idx}")
                    values.append(min_char_count)
                    idx += 1

                if started_at is not None:
                    updates.append(f"started_at = ${idx}")
                    values.append(started_at)
                    idx += 1

                if ended_at is not None:
                    updates.append(f"ended_at = ${idx}")
                    values.append(ended_at)
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
                        group_id, enabled, top_count, min_char_count,
                        started_at, ended_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    group_id,
                    enabled if enabled is not None else False,
                    top_count or 20,
                    min_char_count or 10,
                    started_at,
                    ended_at
                )

            return True
    except Exception as e:
        logger.error(f"❌ Aktivite ayarları kaydetme hatası: {e}")
        return False


async def set_min_char_count(group_id: int, min_char_count: int) -> bool:
    """Minimum karakter sayısını ayarla"""
    if min_char_count < 1:
        min_char_count = 1
    if min_char_count > 100:
        min_char_count = 100
    return await create_or_update_activity_settings(group_id, min_char_count=min_char_count)


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
    limit: int = 20,
    exclude_admin_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Aktivite sıralamasını getir
    BAĞIMSIZ activity_count alanını kullanır
    enabled olup olmadığına bakmaz - her zaman mevcut veriyi döner
    """
    try:
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
    exclude_admin_ids: List[int] = None,
    limit: int = None
) -> List[Dict[str, Any]]:
    """Sıralamayı ödüllerle birlikte getir

    Args:
        limit: Gösterilecek kişi sayısı. None ise settings'den alınır.
    """
    settings = await get_activity_settings(group_id)

    # Limit belirtilmişse onu kullan, değilse settings'den al
    if limit is not None:
        top_count = limit
    else:
        top_count = settings.get('top_count', 20) if settings else 20

    # Sıralamayı al
    users = await get_activity_leaderboard(group_id, top_count, exclude_admin_ids)

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


async def get_user_activity_rank(user_id: int, group_id: int) -> int:
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


async def start_activity_tracking(group_id: int) -> bool:
    """
    Aktivite takibini başlat
    - Tüm kullanıcıların activity_count'unu sıfırla
    - Başlama tarihini kaydet
    - Bitiş tarihini temizle
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
            enabled=True,
            started_at=now,
            ended_at=None  # Bitiş tarihini temizle
        )
    except Exception as e:
        logger.error(f"❌ Aktivite takibi başlatma hatası: {e}")
        return False


async def stop_activity_tracking(group_id: int) -> bool:
    """
    Aktivite takibini durdur
    - enabled = False yap
    - Bitiş tarihini kaydet
    - Veriler silinmez, son sıralama görüntülenebilir
    """
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        return await create_or_update_activity_settings(
            group_id,
            enabled=False,
            ended_at=now
        )
    except Exception as e:
        logger.error(f"❌ Aktivite takibi durdurma hatası: {e}")
        return False


async def get_activity_status(group_id: int) -> Dict[str, Any]:
    """
    Aktivite durumunu detaylı getir
    - enabled: Aktif mi?
    - started_at: Ne zaman başladı?
    - ended_at: Ne zaman bitti?
    - min_char_count: Minimum karakter sayısı
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
                'ended_at': settings.get('ended_at'),
                'top_count': settings.get('top_count', 20),
                'min_char_count': settings.get('min_char_count', 10) or 10,
                'has_data': has_data
            }

        return {
            'enabled': False,
            'started_at': None,
            'ended_at': None,
            'top_count': 20,
            'min_char_count': 10,
            'has_data': has_data
        }
    except Exception as e:
        logger.error(f"❌ Aktivite durumu getirme hatası: {e}")
        return {
            'enabled': False,
            'started_at': None,
            'ended_at': None,
            'top_count': 20,
            'min_char_count': 10,
            'has_data': False
        }

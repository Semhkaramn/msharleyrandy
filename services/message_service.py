"""
📊 Mesaj Sayma Servisi
Kullanıcı mesajlarını sayar ve istatistikleri yönetir
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from database import db
from config import IGNORED_USER_IDS

# Türkiye saat dilimi
TR_TZ = ZoneInfo("Europe/Istanbul")


async def track_message(
    telegram_id: int,
    group_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None
) -> bool:
    """
    Kullanıcı mesajını kaydet ve sayaçları güncelle

    Args:
        telegram_id: Telegram kullanıcı ID
        group_id: Grup ID
        username: Telegram username
        first_name: İsim
        last_name: Soyisim

    Returns:
        bool: Başarılı ise True
    """
    # Sistem hesaplarını sayma
    if telegram_id in IGNORED_USER_IDS:
        return False

    try:
        async with db.pool.acquire() as conn:
            now = datetime.now(timezone.utc).replace(tzinfo=None)  # Naive UTC for DB compatibility

            # Kullanıcı var mı kontrol et
            user = await conn.fetchrow("""
                SELECT id, last_daily_reset, last_weekly_reset, last_monthly_reset
                FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2
            """, telegram_id, group_id)

            if user:
                # Reset kontrolü
                daily_reset = user['last_daily_reset']
                weekly_reset = user['last_weekly_reset']
                monthly_reset = user['last_monthly_reset']

                # Günlük reset (her gün 00:00 UTC+3)
                daily_count_add = 1
                new_daily_reset = daily_reset
                if _should_reset_daily(daily_reset, now):
                    daily_count_add = 1  # Sıfırla ve 1 ekle
                    new_daily_reset = now
                    await conn.execute("""
                        UPDATE telegram_users
                        SET daily_count = 0, last_daily_reset = $1
                        WHERE id = $2
                    """, now, user['id'])

                # Haftalık reset (her Pazartesi 00:00 UTC+3)
                weekly_count_add = 1
                new_weekly_reset = weekly_reset
                if _should_reset_weekly(weekly_reset, now):
                    weekly_count_add = 1
                    new_weekly_reset = now
                    await conn.execute("""
                        UPDATE telegram_users
                        SET weekly_count = 0, last_weekly_reset = $1
                        WHERE id = $2
                    """, now, user['id'])

                # Aylık reset (her ayın 1'i 00:00 UTC+3)
                monthly_count_add = 1
                new_monthly_reset = monthly_reset
                if _should_reset_monthly(monthly_reset, now):
                    monthly_count_add = 1
                    new_monthly_reset = now
                    await conn.execute("""
                        UPDATE telegram_users
                        SET monthly_count = 0, last_monthly_reset = $1
                        WHERE id = $2
                    """, now, user['id'])

                # Aktivite takibi aktif mi kontrol et
                activity_enabled = await conn.fetchval("""
                    SELECT enabled FROM activity_settings WHERE group_id = $1
                """, group_id)

                # Sayaçları güncelle (activity_count dahil)
                if activity_enabled:
                    await conn.execute("""
                        UPDATE telegram_users
                        SET message_count = message_count + 1,
                            daily_count = daily_count + 1,
                            weekly_count = weekly_count + 1,
                            monthly_count = monthly_count + 1,
                            activity_count = activity_count + 1,
                            username = COALESCE($1, username),
                            first_name = COALESCE($2, first_name),
                            last_name = COALESCE($3, last_name),
                            last_message_at = $4,
                            updated_at = $4
                        WHERE id = $5
                    """, username, first_name, last_name, now, user['id'])
                else:
                    await conn.execute("""
                        UPDATE telegram_users
                        SET message_count = message_count + 1,
                            daily_count = daily_count + 1,
                            weekly_count = weekly_count + 1,
                            monthly_count = monthly_count + 1,
                            username = COALESCE($1, username),
                            first_name = COALESCE($2, first_name),
                            last_name = COALESCE($3, last_name),
                            last_message_at = $4,
                            updated_at = $4
                        WHERE id = $5
                    """, username, first_name, last_name, now, user['id'])

            else:
                # Aktivite takibi aktif mi kontrol et
                activity_enabled = await conn.fetchval("""
                    SELECT enabled FROM activity_settings WHERE group_id = $1
                """, group_id)

                # Yeni kullanıcı oluştur (activity_count dahil)
                activity_count = 1 if activity_enabled else 0
                await conn.execute("""
                    INSERT INTO telegram_users (
                        telegram_id, group_id, username, first_name, last_name,
                        message_count, daily_count, weekly_count, monthly_count, activity_count,
                        last_message_at, last_daily_reset, last_weekly_reset, last_monthly_reset, activity_last_reset
                    ) VALUES ($1, $2, $3, $4, $5, 1, 1, 1, 1, $6, $7, $7, $7, $7, $7)
                """, telegram_id, group_id, username, first_name, last_name, activity_count, now)

            return True

    except Exception as e:
        print(f"❌ Mesaj kaydetme hatası: {e}")
        return False


async def get_user_stats(telegram_id: int, group_id: int) -> Optional[Dict[str, Any]]:
    """
    Kullanıcının mesaj istatistiklerini getir
    Reset kontrolü yaparak dönemlerin geçerliliğini kontrol eder

    Args:
        telegram_id: Telegram kullanıcı ID
        group_id: Grup ID

    Returns:
        dict: İstatistikler veya None
    """
    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT username, first_name, last_name,
                       message_count, daily_count, weekly_count, monthly_count,
                       last_message_at, last_daily_reset, last_weekly_reset, last_monthly_reset
                FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2
            """, telegram_id, group_id)

            if not user:
                return None

            # Şu anki zamanı al
            now = datetime.now(timezone.utc).replace(tzinfo=None)  # Naive UTC for DB compatibility

            # Reset kontrolü yap - dönem geçmişse count 0 olmalı
            daily_count = user['daily_count']
            weekly_count = user['weekly_count']
            monthly_count = user['monthly_count']

            # Günlük reset kontrolü
            if user['last_daily_reset'] and _should_reset_daily(user['last_daily_reset'], now):
                daily_count = 0

            # Haftalık reset kontrolü
            if user['last_weekly_reset'] and _should_reset_weekly(user['last_weekly_reset'], now):
                weekly_count = 0

            # Aylık reset kontrolü
            if user['last_monthly_reset'] and _should_reset_monthly(user['last_monthly_reset'], now):
                monthly_count = 0

            return {
                "username": user['username'],
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "total": user['message_count'],
                "daily": daily_count,
                "weekly": weekly_count,
                "monthly": monthly_count,
                "last_message_at": user['last_message_at']
            }

    except Exception as e:
        print(f"❌ İstatistik getirme hatası: {e}")
        return None


async def check_message_requirement(
    telegram_id: int,
    group_id: int,
    requirement_type: str,
    required_count: int
) -> tuple[bool, int]:
    """
    Mesaj şartının karşılanıp karşılanmadığını kontrol et

    Args:
        telegram_id: Telegram kullanıcı ID
        group_id: Grup ID
        requirement_type: Şart tipi (daily, weekly, monthly, all_time)
        required_count: Gerekli mesaj sayısı

    Returns:
        tuple: (Karşılandı mı, Mevcut sayı)
    """
    stats = await get_user_stats(telegram_id, group_id)

    if not stats:
        return False, 0

    if requirement_type == "daily":
        current = stats['daily']
    elif requirement_type == "weekly":
        current = stats['weekly']
    elif requirement_type == "monthly":
        current = stats['monthly']
    else:  # all_time
        current = stats['total']

    return current >= required_count, current


def _get_tr_time(dt: datetime) -> datetime:
    """UTC datetime'ı Türkiye saatine çevir"""
    if dt is None:
        return None
    # UTC olarak işaretle ve TR'ye çevir
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TR_TZ)


def _should_reset_daily(last_reset: datetime, now: datetime) -> bool:
    """Günlük reset gerekli mi kontrol et (Türkiye saati - gece 00:00)"""
    if not last_reset:
        return True

    last_reset_tr = _get_tr_time(last_reset)
    now_tr = _get_tr_time(now)

    return last_reset_tr.date() < now_tr.date()


def _should_reset_weekly(last_reset: datetime, now: datetime) -> bool:
    """Haftalık reset gerekli mi kontrol et (Pazartesi 00:00 TR)"""
    if not last_reset:
        return True

    last_reset_tr = _get_tr_time(last_reset)
    now_tr = _get_tr_time(now)

    # Pazartesi = 0
    last_monday = last_reset_tr.date() - timedelta(days=last_reset_tr.weekday())
    current_monday = now_tr.date() - timedelta(days=now_tr.weekday())

    return last_monday < current_monday


def _should_reset_monthly(last_reset: datetime, now: datetime) -> bool:
    """Aylık reset gerekli mi kontrol et (Ayın 1'i 00:00 TR)"""
    if not last_reset:
        return True

    last_reset_tr = _get_tr_time(last_reset)
    now_tr = _get_tr_time(now)

    return (last_reset_tr.year, last_reset_tr.month) < (now_tr.year, now_tr.month)


async def get_user_randy_stats(telegram_id: int) -> Dict[str, Any]:
    """
    Kullanıcının Randy istatistiklerini getir

    Args:
        telegram_id: Telegram kullanıcı ID

    Returns:
        dict: Randy istatistikleri
    """
    try:
        async with db.pool.acquire() as conn:
            # Katıldığı Randy sayısı (gerçek katılımlar - username veya first_name dolu)
            participated = await conn.fetchval("""
                SELECT COUNT(*) FROM randy_participants
                WHERE telegram_id = $1 AND (username IS NOT NULL OR first_name IS NOT NULL)
            """, telegram_id)

            # Kazandığı Randy sayısı
            won = await conn.fetchval("""
                SELECT COUNT(*) FROM randy_winners
                WHERE telegram_id = $1
            """, telegram_id)

            return {
                "participated": participated or 0,
                "won": won or 0
            }
    except Exception as e:
        print(f"❌ Randy istatistik hatası: {e}")
        return {"participated": 0, "won": 0}


async def get_full_user_stats(telegram_id: int, group_id: int) -> Optional[Dict[str, Any]]:
    """
    Kullanıcının tüm istatistiklerini getir (mesaj + randy)

    Args:
        telegram_id: Telegram kullanıcı ID
        group_id: Grup ID

    Returns:
        dict: Tüm istatistikler veya None
    """
    # Mesaj istatistikleri
    message_stats = await get_user_stats(telegram_id, group_id)

    # Randy istatistikleri
    randy_stats = await get_user_randy_stats(telegram_id)

    if not message_stats:
        # Kullanıcı kayıtlı değil ama Randy istatistikleri olabilir
        return {
            "username": None,
            "first_name": None,
            "last_name": None,
            "total": 0,
            "daily": 0,
            "weekly": 0,
            "monthly": 0,
            "last_message_at": None,
            "randy_participated": randy_stats["participated"],
            "randy_won": randy_stats["won"]
        }

    return {
        **message_stats,
        "randy_participated": randy_stats["participated"],
        "randy_won": randy_stats["won"]
    }


async def is_user_registered(telegram_id: int, group_id: int) -> bool:
    """
    Kullanıcı veritabanında kayıtlı mı?

    Args:
        telegram_id: Telegram kullanıcı ID
        group_id: Grup ID

    Returns:
        bool: Kayıtlı ise True
    """
    try:
        async with db.pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT 1 FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2
                LIMIT 1
            """, telegram_id, group_id)
            return exists is not None
    except Exception as e:
        print(f"❌ Kullanıcı kontrol hatası: {e}")
        return False

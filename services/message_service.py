"""
📊 Mesaj Sayma Servisi
Kullanıcı mesajlarını sayar ve istatistikleri yönetir
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database import db
from config import IGNORED_USER_IDS


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
            now = datetime.utcnow()

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

                # Sayaçları güncelle
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
                # Yeni kullanıcı oluştur
                await conn.execute("""
                    INSERT INTO telegram_users (
                        telegram_id, group_id, username, first_name, last_name,
                        message_count, daily_count, weekly_count, monthly_count,
                        last_message_at, last_daily_reset, last_weekly_reset, last_monthly_reset
                    ) VALUES ($1, $2, $3, $4, $5, 1, 1, 1, 1, $6, $6, $6, $6)
                """, telegram_id, group_id, username, first_name, last_name, now)

            return True

    except Exception as e:
        print(f"❌ Mesaj kaydetme hatası: {e}")
        return False


async def get_user_stats(telegram_id: int, group_id: int) -> Optional[Dict[str, Any]]:
    """
    Kullanıcının mesaj istatistiklerini getir

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
                       last_message_at
                FROM telegram_users
                WHERE telegram_id = $1 AND group_id = $2
            """, telegram_id, group_id)

            if not user:
                return None

            return {
                "username": user['username'],
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "total": user['message_count'],
                "daily": user['daily_count'],
                "weekly": user['weekly_count'],
                "monthly": user['monthly_count'],
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


def _should_reset_daily(last_reset: datetime, now: datetime) -> bool:
    """Günlük reset gerekli mi kontrol et (Türkiye saati)"""
    if not last_reset:
        return True

    # UTC+3 için düzeltme
    tr_offset = timedelta(hours=3)
    last_reset_tr = last_reset + tr_offset
    now_tr = now + tr_offset

    return last_reset_tr.date() < now_tr.date()


def _should_reset_weekly(last_reset: datetime, now: datetime) -> bool:
    """Haftalık reset gerekli mi kontrol et (Pazartesi)"""
    if not last_reset:
        return True

    tr_offset = timedelta(hours=3)
    last_reset_tr = last_reset + tr_offset
    now_tr = now + tr_offset

    # Pazartesi = 0
    last_monday = last_reset_tr.date() - timedelta(days=last_reset_tr.weekday())
    current_monday = now_tr.date() - timedelta(days=now_tr.weekday())

    return last_monday < current_monday


def _should_reset_monthly(last_reset: datetime, now: datetime) -> bool:
    """Aylık reset gerekli mi kontrol et (Ayın 1'i)"""
    if not last_reset:
        return True

    tr_offset = timedelta(hours=3)
    last_reset_tr = last_reset + tr_offset
    now_tr = now + tr_offset

    return (last_reset_tr.year, last_reset_tr.month) < (now_tr.year, now_tr.month)

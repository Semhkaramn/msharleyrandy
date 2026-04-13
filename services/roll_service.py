"""
🎯 Roll Sistemi Servisi
Roll oturumları, adımlar ve kullanıcı takibi
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from database import db
from config import DEFAULT_ROLL_DURATION
from utils.logger import get_logger

logger = get_logger(__name__)


# Status tipleri
STATUS_ACTIVE = 'active'
STATUS_PAUSED = 'paused'
STATUS_STOPPED = 'stopped'
STATUS_BREAK = 'break'
STATUS_LOCKED = 'locked'
STATUS_LOCKED_BREAK = 'locked_break'


async def get_roll_state(group_id: int) -> Dict[str, Any]:
    """
    Roll durumunu getir

    Args:
        group_id: Grup ID

    Returns:
        dict: Roll durumu
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT status, active_duration, current_step, previous_status
                FROM roll_sessions
                WHERE group_id = $1
            """, group_id)

            if not session:
                return {
                    'status': STATUS_STOPPED,
                    'active_duration': DEFAULT_ROLL_DURATION,
                    'current_step': 0,
                    'previous_status': None,
                    'group_id': group_id
                }

            return {
                'status': session['status'],
                'active_duration': session['active_duration'],
                'current_step': session['current_step'],
                'previous_status': session['previous_status'],
                'group_id': group_id
            }

    except Exception as e:
        logger.error(f"❌ Roll state getirme hatası: {e}")
        return {
            'status': STATUS_STOPPED,
            'active_duration': DEFAULT_ROLL_DURATION,
            'current_step': 0,
            'previous_status': None,
            'group_id': group_id
        }


async def start_roll(group_id: int, duration: int) -> bool:
    """
    Roll başlat - Adım 1'i oluştur ve aktif yap

    Args:
        group_id: Grup ID
        duration: Süre (dakika)

    Returns:
        bool: Başarılı ise True
    """
    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                # Mevcut session'ı sil
                await conn.execute("""
                    DELETE FROM roll_sessions WHERE group_id = $1
                """, group_id)

                # Yeni session oluştur
                session_id = await conn.fetchval("""
                    INSERT INTO roll_sessions (group_id, status, active_duration, current_step)
                    VALUES ($1, $2, $3, 1)
                    RETURNING id
                """, group_id, STATUS_ACTIVE, max(1, duration))

                # Adım 1 oluştur
                await conn.execute("""
                    INSERT INTO roll_steps (session_id, step_number, is_active)
                    VALUES ($1, 1, TRUE)
                """, session_id)

                logger.info(f"✅ Roll başlatıldı: Grup={group_id}, Süre={duration}dk")
                return True

    except Exception as e:
        logger.error(f"❌ Roll başlatma hatası: {e}")
        return False


async def pause_roll(group_id: int) -> bool:
    """Roll'u duraklat"""
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session or session['status'] == STATUS_STOPPED:
                return False

            if session['status'] == STATUS_ACTIVE:
                await conn.execute("""
                    UPDATE roll_sessions SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_PAUSED, session['id'])
            elif session['status'] in [STATUS_LOCKED, STATUS_BREAK, STATUS_LOCKED_BREAK]:
                await conn.execute("""
                    UPDATE roll_sessions SET status = $1, previous_status = NULL, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_PAUSED, session['id'])

            return True

    except Exception as e:
        logger.error(f"❌ Roll duraklatma hatası: {e}")
        return False


async def lock_roll(group_id: int) -> Tuple[bool, str]:
    """
    Roll'u kilitle (yeni kullanıcı girişini kapat)

    Returns:
        tuple: (Başarılı mı, Mesaj)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, previous_status FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session or session['status'] == STATUS_STOPPED:
                return False, "aktif_degil"

            if session['status'] in [STATUS_LOCKED, STATUS_LOCKED_BREAK]:
                return False, "zaten_kilitli"

            was_break = session['status'] == STATUS_BREAK

            if session['status'] in [STATUS_ACTIVE, STATUS_PAUSED]:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, previous_status = $2, updated_at = NOW()
                    WHERE id = $3
                """, STATUS_LOCKED, session['status'], session['id'])
            elif session['status'] == STATUS_BREAK:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_LOCKED_BREAK, session['id'])

            return True, "molada" if was_break else "normal"

    except Exception as e:
        logger.error(f"❌ Roll kilitleme hatası: {e}")
        return False, "hata"


async def unlock_roll(group_id: int) -> Tuple[bool, str]:
    """
    Roll kilidini aç

    Returns:
        tuple: (Başarılı mı, Önceki durum)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, previous_status FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session:
                return False, ""

            if session['status'] == STATUS_LOCKED:
                prev_status = session['previous_status'] or STATUS_ACTIVE
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, previous_status = NULL, updated_at = NOW()
                    WHERE id = $2
                """, prev_status, session['id'])
                return True, prev_status

            elif session['status'] == STATUS_LOCKED_BREAK:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_BREAK, session['id'])
                return True, STATUS_BREAK

            return False, ""

    except Exception as e:
        logger.error(f"❌ Roll kilit açma hatası: {e}")
        return False, ""


async def start_break(group_id: int) -> Tuple[bool, str]:
    """
    Mola başlat

    Returns:
        tuple: (Başarılı mı, Mesaj tipi)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, previous_status FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session or session['status'] == STATUS_STOPPED:
                return False, "aktif_degil"

            if session['status'] in [STATUS_BREAK, STATUS_LOCKED_BREAK]:
                return False, "zaten_molada"

            was_locked = session['status'] == STATUS_LOCKED

            if session['status'] in [STATUS_ACTIVE, STATUS_PAUSED]:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, previous_status = $2, updated_at = NOW()
                    WHERE id = $3
                """, STATUS_BREAK, session['status'], session['id'])
            elif session['status'] == STATUS_LOCKED:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_LOCKED_BREAK, session['id'])

            # Tüm kullanıcıların lastActive zamanlarını güncelle
            await conn.execute("""
                UPDATE roll_step_users
                SET last_active = NOW()
                WHERE step_id IN (
                    SELECT rs.id FROM roll_steps rs
                    JOIN roll_sessions s ON rs.session_id = s.id
                    WHERE s.group_id = $1
                )
            """, group_id)

            return True, "kilitli" if was_locked else "normal"

    except Exception as e:
        logger.error(f"❌ Mola başlatma hatası: {e}")
        return False, "hata"


async def resume_roll(group_id: int) -> Tuple[bool, str, int]:
    """
    Moladan devam et / Yeni adım oluştur

    Returns:
        tuple: (Başarılı mı, Yeni durum, Aktif süre)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, previous_status, current_step, active_duration
                FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session:
                return False, "", 0

            duration = session['active_duration']

            if session['status'] == STATUS_BREAK:
                new_status = session['previous_status'] or STATUS_ACTIVE
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, previous_status = NULL, updated_at = NOW()
                    WHERE id = $2
                """, new_status, session['id'])

                # LastActive güncelle
                await _update_all_last_active(conn, group_id)

                return True, new_status, duration

            elif session['status'] == STATUS_LOCKED_BREAK:
                await conn.execute("""
                    UPDATE roll_sessions
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, STATUS_LOCKED, session['id'])

                await _update_all_last_active(conn, group_id)

                return True, STATUS_LOCKED, duration

            elif session['status'] == STATUS_PAUSED:
                # Yeni adım oluştur
                new_step = session['current_step'] + 1

                async with conn.transaction():
                    # Mevcut aktif adımları kapat
                    await conn.execute("""
                        UPDATE roll_steps SET is_active = FALSE
                        WHERE session_id = $1 AND is_active = TRUE
                    """, session['id'])

                    # Yeni adım oluştur
                    await conn.execute("""
                        INSERT INTO roll_steps (session_id, step_number, is_active)
                        VALUES ($1, $2, TRUE)
                    """, session['id'], new_step)

                    # Session güncelle
                    await conn.execute("""
                        UPDATE roll_sessions
                        SET status = $1, current_step = $2, previous_status = NULL, updated_at = NOW()
                        WHERE id = $3
                    """, STATUS_ACTIVE, new_step, session['id'])

                await _update_all_last_active(conn, group_id)

                return True, STATUS_ACTIVE, duration

            return False, "", 0

    except Exception as e:
        logger.error(f"❌ Roll devam hatası: {e}")
        return False, "", 0


async def save_step(group_id: int) -> Tuple[bool, str, int]:
    """
    Adım kaydet - Mevcut aktif adımı kapat

    Returns:
        tuple: (Başarılı mı, Mesaj, Adım numarası)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, active_duration, current_step
                FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session or session['status'] == STATUS_STOPPED:
                return False, "aktif_degil", 0

            # Aktif adımı bul
            step = await conn.fetchrow("""
                SELECT id, step_number FROM roll_steps
                WHERE session_id = $1 AND is_active = TRUE
            """, session['id'])

            if not step:
                return False, "adim_yok", 0

            # Önce inaktif kullanıcıları temizle (MOLA durumlarında temizlik YAPILMAZ!)
            # LOCKED_BREAK = mola + kilit, kullanıcılar mesaj yazamaz, silinmemeli
            if session['status'] in [STATUS_ACTIVE, STATUS_LOCKED]:
                await clean_inactive_users(group_id)

            # Kullanıcı sayısını kontrol et
            user_count = await conn.fetchval("""
                SELECT COUNT(*) FROM roll_step_users WHERE step_id = $1
            """, step['id'])

            if user_count == 0:
                return False, "kullanici_yok", 0

            # Adımı kapat ve roll'u duraklat
            async with conn.transaction():
                await conn.execute("""
                    UPDATE roll_steps SET is_active = FALSE WHERE id = $1
                """, step['id'])

                await conn.execute("""
                    UPDATE roll_sessions SET status = $1, updated_at = NOW() WHERE id = $2
                """, STATUS_PAUSED, session['id'])

            return True, "kaydedildi", step['step_number']

    except Exception as e:
        logger.error(f"❌ Adım kaydetme hatası: {e}")
        return False, "hata", 0


async def stop_roll(group_id: int) -> bool:
    """Roll'u sonlandır"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE roll_sessions SET status = $1, updated_at = NOW()
                WHERE group_id = $2
            """, STATUS_STOPPED, group_id)
            return True

    except Exception as e:
        logger.error(f"❌ Roll durdurma hatası: {e}")
        return False


async def track_user_message(
    group_id: int,
    user_id: int,
    username: str,
    first_name: str
) -> bool:
    """
    Kullanıcı mesajını roll için takip et

    Args:
        group_id: Grup ID
        user_id: Telegram kullanıcı ID
        username: Username
        first_name: İsim

    Returns:
        bool: Başarılı ise True
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, active_duration FROM roll_sessions
                WHERE group_id = $1
            """, group_id)

            if not session:
                return False

            # Sadece active, locked veya locked_break'te izle
            if session['status'] not in [STATUS_ACTIVE, STATUS_LOCKED, STATUS_LOCKED_BREAK]:
                return False

            # Aktif adımı bul
            step = await conn.fetchrow("""
                SELECT id FROM roll_steps
                WHERE session_id = $1 AND is_active = TRUE
            """, session['id'])

            if not step:
                return False

            name = f"@{username}" if username else first_name or "Kullanıcı"
            now = datetime.utcnow()

            # Kilitli durumlarda sadece mevcut kullanıcıları güncelle
            if session['status'] in [STATUS_LOCKED, STATUS_LOCKED_BREAK]:
                result = await conn.execute("""
                    UPDATE roll_step_users
                    SET last_active = $1, message_count = message_count + 1, name = $2
                    WHERE step_id = $3 AND telegram_user_id = $4
                """, now, name, step['id'], user_id)

                # Affected rows = 0 ise kullanıcı yok (yeni kullanıcı eklenmiyor)
                return True

            # Active durumda: upsert
            await conn.execute("""
                INSERT INTO roll_step_users (step_id, telegram_user_id, name, message_count, last_active)
                VALUES ($1, $2, $3, 1, $4)
                ON CONFLICT (step_id, telegram_user_id)
                DO UPDATE SET
                    last_active = $4,
                    message_count = roll_step_users.message_count + 1,
                    name = $3
            """, step['id'], user_id, name, now)

            return True

    except Exception as e:
        logger.error(f"❌ Roll mesaj takip hatası: {e}")
        return False


async def clean_inactive_users(group_id: int) -> int:
    """
    İnaktif kullanıcıları temizle

    Returns:
        int: Silinen kullanıcı sayısı
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, active_duration FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session:
                return 0

            timeout_minutes = session['active_duration']
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

            # İnaktif kullanıcıları sil
            result = await conn.execute("""
                DELETE FROM roll_step_users
                WHERE step_id IN (
                    SELECT id FROM roll_steps WHERE session_id = $1
                )
                AND last_active < $2
            """, session['id'], cutoff_time)

            # Boş adımları sil (aktif olmayanlar)
            await conn.execute("""
                DELETE FROM roll_steps
                WHERE session_id = $1
                AND is_active = FALSE
                AND NOT EXISTS (
                    SELECT 1 FROM roll_step_users WHERE step_id = roll_steps.id
                )
            """, session['id'])

            deleted = int(result.split()[-1]) if result else 0
            return deleted

    except Exception as e:
        logger.error(f"❌ İnaktif temizleme hatası: {e}")
        return 0


async def get_status_list(group_id: int, return_raw: bool = False) -> Tuple[str, List[Dict], Dict]:
    """
    Roll durumu ve kullanıcı listesini getir

    Args:
        group_id: Grup ID
        return_raw: True ise ham veriyi döndür (mesaj formatlaması için)

    Returns:
        tuple: (Durum metni, Adımlar listesi, Session bilgisi)
    """
    try:
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow("""
                SELECT id, status, active_duration, current_step, created_at
                FROM roll_sessions WHERE group_id = $1
            """, group_id)

            if not session:
                return "stopped", [], {}

            # Aktif durumlarda temizlik yap (MOLA durumlarında temizlik YAPILMAZ!)
            # LOCKED_BREAK = mola + kilit, kullanıcılar mesaj yazamaz, silinmemeli
            if session['status'] in [STATUS_ACTIVE, STATUS_LOCKED]:
                await clean_inactive_users(group_id)

            # Adımları getir
            steps = await conn.fetch("""
                SELECT id, step_number, is_active, created_at
                FROM roll_steps
                WHERE session_id = $1
                ORDER BY step_number ASC
            """, session['id'])

            result_steps = []
            for step in steps:
                users = await conn.fetch("""
                    SELECT telegram_user_id, name, message_count
                    FROM roll_step_users
                    WHERE step_id = $1
                    ORDER BY message_count DESC
                """, step['id'])

                result_steps.append({
                    'step_number': step['step_number'],
                    'is_active': step['is_active'],
                    'created_at': step['created_at'],
                    'users': [dict(u) for u in users]
                })

            # Session bilgisini döndür
            session_info = {
                'status': session['status'],
                'active_duration': session['active_duration'],
                'current_step': session['current_step'],
                'created_at': session['created_at']
            }

            return session['status'], result_steps, session_info

    except Exception as e:
        logger.error(f"❌ Status list hatası: {e}")
        return "error", [], {}


async def _update_all_last_active(conn, group_id: int):
    """Tüm kullanıcıların lastActive zamanlarını güncelle"""
    await conn.execute("""
        UPDATE roll_step_users
        SET last_active = NOW()
        WHERE step_id IN (
            SELECT rs.id FROM roll_steps rs
            JOIN roll_sessions s ON rs.session_id = s.id
            WHERE s.group_id = $1
        )
    """, group_id)

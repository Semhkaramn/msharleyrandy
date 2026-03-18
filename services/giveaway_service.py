"""
🎁 Çekiliş (Giveaway) Servisi
Rastgele zamanlı otomatik çekiliş sistemi

Nasıl çalışır:
1. Admin çekiliş başlatır (örn: 2 saat, 3 kazanan)
2. Sistem 2 saat içinde 3 rastgele zaman belirler
3. O zamanlarda gruba mesaj yazan İLK kişi kazanır
4. Kazanan kişinin mesajına reply atılır
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from database import db
from telegram import Bot
from telegram.error import TelegramError, BadRequest

# Aktif çekiliş task'ları
# {giveaway_id: asyncio.Task}
active_giveaway_tasks: Dict[int, asyncio.Task] = {}

# Şu anda kazanma beklenen zaman slotları
# {group_id: {slot_id: win_time}}
pending_win_slots: Dict[int, Dict[int, datetime]] = {}


# ============================================
# AYARLAR YÖNETİMİ
# ============================================

async def get_giveaway_settings(group_id: int) -> Optional[Dict[str, Any]]:
    """Grup çekiliş ayarlarını getir"""
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow("""
                SELECT * FROM giveaway_settings WHERE group_id = $1
            """, group_id)
            return dict(settings) if settings else None
    except Exception as e:
        print(f"❌ Çekiliş ayarları getirme hatası: {e}")
        return None


async def save_giveaway_settings(
    group_id: int,
    admin_group_id: int = None,
    default_duration_hours: int = 2,
    default_winner_count: int = 1,
    max_wins_per_user: int = 0,
    pin_announcement: bool = True,
    pin_winner_message: bool = True,
    pin_in_admin_group: bool = True,
    notify_admin_group: bool = True,
    winner_message_template: str = None
) -> bool:
    """Grup çekiliş ayarlarını kaydet"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO giveaway_settings (
                    group_id, admin_group_id, default_duration_hours, default_winner_count,
                    max_wins_per_user, pin_announcement, pin_winner_message,
                    pin_in_admin_group, notify_admin_group, winner_message_template, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                ON CONFLICT (group_id)
                DO UPDATE SET
                    admin_group_id = COALESCE($2, giveaway_settings.admin_group_id),
                    default_duration_hours = $3,
                    default_winner_count = $4,
                    max_wins_per_user = $5,
                    pin_announcement = $6,
                    pin_winner_message = $7,
                    pin_in_admin_group = $8,
                    notify_admin_group = $9,
                    winner_message_template = COALESCE($10, giveaway_settings.winner_message_template),
                    updated_at = NOW()
            """, group_id, admin_group_id, default_duration_hours, default_winner_count,
                max_wins_per_user, pin_announcement, pin_winner_message,
                pin_in_admin_group, notify_admin_group, winner_message_template)
            return True
    except Exception as e:
        print(f"❌ Çekiliş ayarları kaydetme hatası: {e}")
        return False


async def update_giveaway_setting(group_id: int, **kwargs) -> bool:
    """Tek bir ayarı güncelle"""
    # İzin verilen alan isimleri (SQL injection koruması)
    ALLOWED_FIELDS = {
        'admin_group_id', 'default_duration_hours', 'default_winner_count',
        'max_wins_per_user', 'pin_announcement', 'pin_winner_message',
        'pin_in_admin_group', 'notify_admin_group', 'winner_message_template'
    }

    try:
        async with db.pool.acquire() as conn:
            # Önce mevcut ayarları kontrol et, yoksa oluştur
            existing = await conn.fetchval("""
                SELECT id FROM giveaway_settings WHERE group_id = $1
            """, group_id)

            if not existing:
                await conn.execute("""
                    INSERT INTO giveaway_settings (group_id) VALUES ($1)
                """, group_id)

            # Ayarları güncelle (sadece izin verilen alanlar)
            for key, value in kwargs.items():
                if key not in ALLOWED_FIELDS:
                    print(f"⚠️ Geçersiz alan adı: {key}")
                    continue
                await conn.execute(f"""
                    UPDATE giveaway_settings SET {key} = $1, updated_at = NOW()
                    WHERE group_id = $2
                """, value, group_id)

            return True
    except Exception as e:
        print(f"❌ Çekiliş ayarı güncelleme hatası: {e}")
        return False


# ============================================
# ÇEKİLİŞ YÖNETİMİ
# ============================================

async def create_giveaway(
    group_id: int,
    creator_id: int,
    prize_text: str,
    duration_hours: int,
    winner_count: int,
    max_wins_per_user: int = 0,
    pin_announcement: bool = True,
    pin_winner_message: bool = True,
    notify_admin_group: bool = True,
    pin_in_admin_group: bool = True
) -> Tuple[bool, Optional[Dict]]:
    """
    Yeni çekiliş oluştur ve rastgele kazanma zamanları belirle

    Returns:
        tuple: (Başarılı mı, Çekiliş bilgileri)
    """
    try:
        async with db.pool.acquire() as conn:
            # Aktif çekiliş var mı kontrol et
            existing = await conn.fetchval("""
                SELECT id FROM giveaways WHERE group_id = $1 AND status = 'active'
            """, group_id)

            if existing:
                return False, {"error": "already_active"}

            # UTC zamanı al ve naive'e çevir (DB uyumluluğu için)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            ends_at = now + timedelta(hours=duration_hours)

            # Çekiliş oluştur
            giveaway_id = await conn.fetchval("""
                INSERT INTO giveaways (
                    group_id, creator_id, prize_text, duration_hours, winner_count,
                    max_wins_per_user, pin_announcement, pin_winner_message,
                    notify_admin_group, pin_in_admin_group, started_at, ends_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """, group_id, creator_id, prize_text, duration_hours, winner_count,
                max_wins_per_user, pin_announcement, pin_winner_message,
                notify_admin_group, pin_in_admin_group, now, ends_at)

            # Rastgele kazanma zamanları oluştur
            win_times = _generate_random_win_times(now, ends_at, winner_count)

            for i, win_time in enumerate(win_times, 1):
                await conn.execute("""
                    INSERT INTO giveaway_win_times (giveaway_id, win_time, slot_number)
                    VALUES ($1, $2, $3)
                """, giveaway_id, win_time, i)

            return True, {
                "id": giveaway_id,
                "group_id": group_id,
                "prize_text": prize_text,
                "duration_hours": duration_hours,
                "winner_count": winner_count,
                "started_at": now,
                "ends_at": ends_at,
                "win_times": win_times
            }

    except Exception as e:
        print(f"❌ Çekiliş oluşturma hatası: {e}")
        return False, None


def _generate_random_win_times(start: datetime, end: datetime, count: int) -> List[datetime]:
    """
    Başlangıç ve bitiş arasında rastgele zamanlar oluştur
    Zamanlar en az 5 dakika arayla olur
    """
    total_seconds = int((end - start).total_seconds())

    # En az 5 dakika (300 saniye) ara ile zamanlar oluştur
    min_gap = 300

    # Minimum ve maksimum offset hesapla
    # İlk 5 dk ve son 2 dk'yı hariç tutmaya çalış ama süre yetmezse esneklik göster
    min_offset = min(300, total_seconds // 4)  # İlk 5 dk veya toplam sürenin 1/4'ü
    max_offset = max(120, total_seconds // 10)  # Son 2 dk veya toplam sürenin 1/10'u

    # Kullanılabilir aralık çok kısa mı?
    usable_range = total_seconds - min_offset - max_offset
    if usable_range < 60:
        # Çok kısa süre, eşit aralıklarla dağıt
        interval = total_seconds // (count + 1)
        return [start + timedelta(seconds=interval * (i + 1)) for i in range(count)]

    # Kullanılabilir zaman aralıklarını hesapla
    if usable_range < (count * min_gap):
        # Yeterli süre yok, eşit aralıklarla dağıt
        interval = total_seconds // (count + 1)
        return [start + timedelta(seconds=interval * (i + 1)) for i in range(count)]

    times = []
    used_seconds = set()

    for _ in range(count):
        attempts = 0
        while attempts < 100:
            # Rastgele saniye seç
            rand_seconds = random.randint(min_offset, total_seconds - max_offset)

            # Bu zaman diğer zamanlarla çakışıyor mu?
            too_close = False
            for used in used_seconds:
                if abs(rand_seconds - used) < min_gap:
                    too_close = True
                    break

            if not too_close:
                used_seconds.add(rand_seconds)
                times.append(start + timedelta(seconds=rand_seconds))
                break

            attempts += 1

        # 100 denemede bulunamadıysa, boş bir zaman bul
        if attempts >= 100:
            for s in range(min_offset, total_seconds - max_offset, 60):
                valid = True
                for used in used_seconds:
                    if abs(s - used) < min_gap:
                        valid = False
                        break
                if valid:
                    used_seconds.add(s)
                    times.append(start + timedelta(seconds=s))
                    break

    # Zamanları sırala
    times.sort()
    return times


async def get_active_giveaway(group_id: int) -> Optional[Dict[str, Any]]:
    """Grupta aktif çekilişi getir"""
    try:
        async with db.pool.acquire() as conn:
            giveaway = await conn.fetchrow("""
                SELECT * FROM giveaways WHERE group_id = $1 AND status = 'active'
            """, group_id)
            return dict(giveaway) if giveaway else None
    except Exception as e:
        print(f"❌ Aktif çekiliş getirme hatası: {e}")
        return None


async def get_giveaway_by_id(giveaway_id: int) -> Optional[Dict[str, Any]]:
    """Çekilişi ID ile getir"""
    try:
        async with db.pool.acquire() as conn:
            giveaway = await conn.fetchrow("""
                SELECT * FROM giveaways WHERE id = $1
            """, giveaway_id)
            return dict(giveaway) if giveaway else None
    except Exception as e:
        print(f"❌ Çekiliş getirme hatası: {e}")
        return None


async def get_giveaway_win_times(giveaway_id: int) -> List[Dict[str, Any]]:
    """Çekilişin kazanma zamanlarını getir"""
    try:
        async with db.pool.acquire() as conn:
            times = await conn.fetch("""
                SELECT * FROM giveaway_win_times
                WHERE giveaway_id = $1
                ORDER BY win_time
            """, giveaway_id)
            return [dict(t) for t in times]
    except Exception as e:
        print(f"❌ Kazanma zamanları getirme hatası: {e}")
        return []


async def get_pending_win_slot(group_id: int) -> Optional[Dict[str, Any]]:
    """
    Şu anda aktif olan ve henüz kazanılmamış slot'u getir
    (win_time geçmiş ve is_won = False)
    """
    try:
        # UTC zamanı al ve naive'e çevir (DB uyumluluğu için)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with db.pool.acquire() as conn:
            slot = await conn.fetchrow("""
                SELECT wt.*, g.prize_text, g.pin_winner_message, g.notify_admin_group, g.pin_in_admin_group
                FROM giveaway_win_times wt
                JOIN giveaways g ON wt.giveaway_id = g.id
                WHERE g.group_id = $1 AND g.status = 'active'
                AND wt.win_time <= $2 AND wt.is_won = FALSE
                ORDER BY wt.win_time
                LIMIT 1
            """, group_id, now)

            return dict(slot) if slot else None
    except Exception as e:
        print(f"❌ Bekleyen slot getirme hatası: {e}")
        return None


async def check_user_win_eligibility(group_id: int, user_id: int, max_wins: int) -> bool:
    """
    Kullanıcının kazanma limiti dolmuş mu kontrol et

    Args:
        group_id: Grup ID
        user_id: Kullanıcı ID
        max_wins: Maksimum kazanma sayısı (0 = sınırsız)

    Returns:
        bool: Kazanabilir mi
    """
    if max_wins == 0:
        return True  # Sınır yok

    try:
        async with db.pool.acquire() as conn:
            win_count = await conn.fetchval("""
                SELECT win_count FROM giveaway_user_wins
                WHERE group_id = $1 AND user_id = $2
            """, group_id, user_id)

            if win_count is None:
                return True

            return win_count < max_wins
    except Exception as e:
        print(f"❌ Kazanma limiti kontrol hatası: {e}")
        return True


async def record_winner(
    slot_id: int,
    giveaway_id: int,
    group_id: int,
    user_id: int,
    username: str,
    first_name: str,
    message_id: int,
    reply_message_id: int = None
) -> bool:
    """Kazananı kaydet"""
    try:
        # UTC zamanı al ve naive'e çevir (DB uyumluluğu için)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with db.pool.acquire() as conn:
            # Slot'u güncelle
            await conn.execute("""
                UPDATE giveaway_win_times
                SET winner_id = $1, winner_username = $2, winner_first_name = $3,
                    winner_message_id = $4, reply_message_id = $5, is_won = TRUE, won_at = $6
                WHERE id = $7
            """, user_id, username, first_name, message_id, reply_message_id, now, slot_id)

            # Kullanıcı kazanma sayısını artır
            await conn.execute("""
                INSERT INTO giveaway_user_wins (group_id, user_id, win_count, last_win_at)
                VALUES ($1, $2, 1, $3)
                ON CONFLICT (group_id, user_id)
                DO UPDATE SET win_count = giveaway_user_wins.win_count + 1, last_win_at = $3
            """, group_id, user_id, now)

            # Tüm slotlar doldu mu kontrol et
            remaining = await conn.fetchval("""
                SELECT COUNT(*) FROM giveaway_win_times
                WHERE giveaway_id = $1 AND is_won = FALSE
            """, giveaway_id)

            if remaining == 0:
                # Çekiliş bitti
                await conn.execute("""
                    UPDATE giveaways SET status = 'ended', ended_at = $1
                    WHERE id = $2
                """, now, giveaway_id)

            return True
    except Exception as e:
        print(f"❌ Kazanan kaydetme hatası: {e}")
        return False


async def end_giveaway(giveaway_id: int) -> bool:
    """Çekilişi sonlandır"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE giveaways SET status = 'ended', ended_at = NOW()
                WHERE id = $1
            """, giveaway_id)
            return True
    except Exception as e:
        print(f"❌ Çekiliş sonlandırma hatası: {e}")
        return False


async def cancel_giveaway(giveaway_id: int) -> bool:
    """Çekilişi iptal et"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE giveaways SET status = 'cancelled', ended_at = NOW()
                WHERE id = $1
            """, giveaway_id)
            return True
    except Exception as e:
        print(f"❌ Çekiliş iptal hatası: {e}")
        return False


# ============================================
# GEÇMİŞ VE İSTATİSTİKLER
# ============================================

async def get_past_giveaways(group_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Geçmiş çekilişleri getir"""
    try:
        async with db.pool.acquire() as conn:
            giveaways = await conn.fetch("""
                SELECT * FROM giveaways
                WHERE group_id = $1 AND status IN ('ended', 'cancelled')
                ORDER BY ended_at DESC
                LIMIT $2
            """, group_id, limit)
            return [dict(g) for g in giveaways]
    except Exception as e:
        print(f"❌ Geçmiş çekilişler hatası: {e}")
        return []


async def get_giveaway_winners(giveaway_id: int) -> List[Dict[str, Any]]:
    """Çekilişin kazananlarını getir"""
    try:
        async with db.pool.acquire() as conn:
            winners = await conn.fetch("""
                SELECT * FROM giveaway_win_times
                WHERE giveaway_id = $1 AND is_won = TRUE
                ORDER BY won_at
            """, giveaway_id)
            return [dict(w) for w in winners]
    except Exception as e:
        print(f"❌ Kazananlar getirme hatası: {e}")
        return []


async def get_user_total_wins(group_id: int, user_id: int) -> int:
    """Kullanıcının toplam kazanma sayısını getir"""
    try:
        async with db.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT win_count FROM giveaway_user_wins
                WHERE group_id = $1 AND user_id = $2
            """, group_id, user_id)
            return count or 0
    except Exception as e:
        print(f"❌ Kullanıcı kazanma sayısı hatası: {e}")
        return 0


async def get_top_winners(group_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """En çok kazanan kullanıcıları getir"""
    try:
        async with db.pool.acquire() as conn:
            winners = await conn.fetch("""
                SELECT uw.user_id, uw.win_count, uw.last_win_at,
                       tu.username, tu.first_name
                FROM giveaway_user_wins uw
                LEFT JOIN telegram_users tu ON uw.user_id = tu.telegram_id AND uw.group_id = tu.group_id
                WHERE uw.group_id = $1
                ORDER BY uw.win_count DESC
                LIMIT $2
            """, group_id, limit)
            return [dict(w) for w in winners]
    except Exception as e:
        print(f"❌ En çok kazananlar hatası: {e}")
        return []


# ============================================
# ÇEKİLİŞ TASK YÖNETİMİ
# ============================================

async def start_giveaway_watcher(giveaway_id: int, group_id: int, bot: Bot):
    """
    Çekiliş için izleme task'ı başlat
    Bu task, çekiliş süresinin sonunda otomatik olarak çekilişi bitirir
    """
    # Mevcut task varsa iptal et
    if giveaway_id in active_giveaway_tasks:
        task = active_giveaway_tasks[giveaway_id]
        if not task.done():
            task.cancel()

    async def watcher_task():
        try:
            giveaway = await get_giveaway_by_id(giveaway_id)
            if not giveaway:
                return

            ends_at = giveaway['ends_at']
            # DB'den gelen tarihler naive (UTC), aware'e çevirip karşılaştır
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)

            # Bitiş zamanına kadar bekle
            wait_seconds = (ends_at - now).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            # Çekiliş hala aktif mi kontrol et
            giveaway = await get_giveaway_by_id(giveaway_id)
            if giveaway and giveaway['status'] == 'active':
                # Kazanılmamış slotları kontrol et
                win_times = await get_giveaway_win_times(giveaway_id)
                unwon_slots = [wt for wt in win_times if not wt['is_won']]

                if unwon_slots:
                    # Kazanılmamış slotlar için uyarı gönder
                    try:
                        slot_text = ", ".join([
                            f"Slot {wt['slot_number']}" for wt in unwon_slots
                        ])
                        await bot.send_message(
                            group_id,
                            f"⏰ <b>Çekiliş Süresi Doldu!</b>\n\n"
                            f"Kazanılamayan slotlar: {slot_text}\n"
                            f"Bu slotlarda o zamanda mesaj yazan olmadığı için kazanan belirlenemedi.",
                            parse_mode="HTML"
                        )
                    except TelegramError as e:
                        print(f"❌ Çekiliş bitiş mesajı hatası: {e}")

                # Çekilişi bitir
                await end_giveaway(giveaway_id)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Çekiliş watcher hatası: {e}")
        finally:
            active_giveaway_tasks.pop(giveaway_id, None)

    task = asyncio.create_task(watcher_task())
    active_giveaway_tasks[giveaway_id] = task


def stop_giveaway_watcher(giveaway_id: int):
    """Çekiliş watcher'ı durdur"""
    if giveaway_id in active_giveaway_tasks:
        task = active_giveaway_tasks[giveaway_id]
        if not task.done():
            task.cancel()
        active_giveaway_tasks.pop(giveaway_id, None)


async def restart_active_giveaways(bot: Bot):
    """
    Bot restart olduğunda aktif çekilişleri yeniden başlat
    """
    try:
        async with db.pool.acquire() as conn:
            active_giveaways = await conn.fetch("""
                SELECT id, group_id FROM giveaways WHERE status = 'active'
            """)

            for giveaway in active_giveaways:
                await start_giveaway_watcher(giveaway['id'], giveaway['group_id'], bot)
                print(f"🎁 Çekiliş watcher yeniden başlatıldı: {giveaway['id']}")

    except Exception as e:
        print(f"❌ Aktif çekilişleri yeniden başlatma hatası: {e}")


# ============================================
# MESAJ KONTROL (handle_message'dan çağrılır)
# ============================================

async def check_and_award_winner(
    group_id: int,
    user_id: int,
    username: str,
    first_name: str,
    message_id: int,
    bot: Bot,
    is_bot: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Kullanıcının mesajını kontrol et, kazanma zamanı geldiyse ödül ver

    Returns:
        dict: Kazanma bilgileri veya None
    """
    # Bot'lar katılamaz
    if is_bot:
        return None

    # Aktif çekiliş var mı?
    giveaway = await get_active_giveaway(group_id)
    if not giveaway:
        return None

    # Bekleyen (zamanı gelmiş ama kazanılmamış) slot var mı?
    slot = await get_pending_win_slot(group_id)
    if not slot:
        return None

    # Kullanıcı kazanma limiti dolmuş mu?
    max_wins = giveaway.get('max_wins_per_user', 0)
    if not await check_user_win_eligibility(group_id, user_id, max_wins):
        return None

    # KAZANDI!
    # Kazananı kaydet
    await record_winner(
        slot_id=slot['id'],
        giveaway_id=slot['giveaway_id'],
        group_id=group_id,
        user_id=user_id,
        username=username,
        first_name=first_name,
        message_id=message_id
    )

    return {
        "slot": slot,
        "giveaway": giveaway,
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "message_id": message_id,
        "prize_text": slot.get('prize_text') or giveaway.get('prize_text'),
        "pin_winner_message": slot.get('pin_winner_message', giveaway.get('pin_winner_message', True)),
        "notify_admin_group": slot.get('notify_admin_group', giveaway.get('notify_admin_group', True)),
        "pin_in_admin_group": slot.get('pin_in_admin_group', giveaway.get('pin_in_admin_group', True))
    }


async def update_announcement_message_id(giveaway_id: int, message_id: int) -> bool:
    """Duyuru mesaj ID'sini kaydet"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE giveaways SET announcement_message_id = $1 WHERE id = $2
            """, message_id, giveaway_id)
            return True
    except Exception as e:
        print(f"❌ Duyuru mesaj ID güncelleme hatası: {e}")
        return False


async def update_slot_reply_message_id(slot_id: int, reply_message_id: int) -> bool:
    """Slot reply mesaj ID'sini kaydet"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE giveaway_win_times SET reply_message_id = $1 WHERE id = $2
            """, reply_message_id, slot_id)
            return True
    except Exception as e:
        print(f"❌ Slot reply mesaj ID güncelleme hatası: {e}")
        return False

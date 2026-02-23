"""
🎲 Randy (Çekiliş) Servisi
Randy oluşturma, başlatma, katılım ve sonlandırma işlemleri
"""

import random
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from database import db
from services.message_service import get_user_stats, check_message_requirement


# Status tipleri
STATUS_DRAFT = 'draft'
STATUS_ACTIVE = 'active'
STATUS_ENDED = 'ended'


# ============================================
# TASLAK YÖNETİMİ (Özelden ayarlama)
# ============================================

async def create_draft(creator_id: int) -> int:
    """
    Yeni Randy taslağı oluştur

    Args:
        creator_id: Oluşturan kullanıcı ID

    Returns:
        int: Taslak ID
    """
    try:
        async with db.pool.acquire() as conn:
            # Mevcut taslağı sil
            await conn.execute("""
                DELETE FROM randy_drafts WHERE creator_id = $1
            """, creator_id)

            # Yeni taslak oluştur
            draft_id = await conn.fetchval("""
                INSERT INTO randy_drafts (creator_id, current_step)
                VALUES ($1, 'group_select')
                RETURNING id
            """, creator_id)

            return draft_id

    except Exception as e:
        print(f"❌ Taslak oluşturma hatası: {e}")
        return 0


async def get_draft(creator_id: int) -> Optional[Dict[str, Any]]:
    """Kullanıcının taslağını getir"""
    try:
        async with db.pool.acquire() as conn:
            draft = await conn.fetchrow("""
                SELECT * FROM randy_drafts WHERE creator_id = $1
            """, creator_id)

            if draft:
                return dict(draft)
            return None

    except Exception as e:
        print(f"❌ Taslak getirme hatası: {e}")
        return None


async def update_draft(creator_id: int, **kwargs) -> bool:
    """Taslağı güncelle"""
    try:
        async with db.pool.acquire() as conn:
            set_clauses = []
            values = []
            i = 1

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ${i}")
                values.append(value)
                i += 1

            values.append(creator_id)

            await conn.execute(f"""
                UPDATE randy_drafts
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE creator_id = ${i}
            """, *values)

            return True

    except Exception as e:
        print(f"❌ Taslak güncelleme hatası: {e}")
        return False


async def delete_draft(creator_id: int) -> bool:
    """Taslağı sil"""
    try:
        async with db.pool.acquire() as conn:
            # Önce taslak ID'sini al
            draft = await conn.fetchrow("""
                SELECT id FROM randy_drafts WHERE creator_id = $1
            """, creator_id)

            if draft:
                # Taslağa bağlı kanalları sil
                await conn.execute("""
                    DELETE FROM randy_channels WHERE randy_draft_id = $1
                """, draft['id'])

            # Taslağı sil
            await conn.execute("""
                DELETE FROM randy_drafts WHERE creator_id = $1
            """, creator_id)
            return True

    except Exception as e:
        print(f"❌ Taslak silme hatası: {e}")
        return False


# ============================================
# KANAL YÖNETİMİ
# ============================================

async def add_channel_to_draft(
    creator_id: int,
    channel_id: int,
    channel_username: str = None,
    channel_title: str = None
) -> Tuple[bool, str]:
    """
    Taslağa kanal ekle

    Args:
        creator_id: Taslak sahibi
        channel_id: Kanal ID
        channel_username: Kanal kullanıcı adı (@olmadan)
        channel_title: Kanal başlığı

    Returns:
        tuple: (Başarılı mı, Mesaj)
    """
    try:
        draft = await get_draft(creator_id)
        if not draft:
            return False, "Taslak bulunamadı"

        async with db.pool.acquire() as conn:
            # Kanal zaten ekli mi?
            existing = await conn.fetchval("""
                SELECT id FROM randy_channels
                WHERE randy_draft_id = $1 AND channel_id = $2
            """, draft['id'], channel_id)

            if existing:
                return False, "Bu kanal zaten ekli"

            # Kanalı ekle
            await conn.execute("""
                INSERT INTO randy_channels (randy_draft_id, channel_id, channel_username, channel_title)
                VALUES ($1, $2, $3, $4)
            """, draft['id'], channel_id, channel_username, channel_title)

            return True, "Kanal eklendi"

    except Exception as e:
        print(f"❌ Kanal ekleme hatası: {e}")
        return False, str(e)


async def remove_channel_from_draft(creator_id: int, channel_id: int) -> bool:
    """Taslaktan kanal sil"""
    try:
        draft = await get_draft(creator_id)
        if not draft:
            return False

        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM randy_channels
                WHERE randy_draft_id = $1 AND channel_id = $2
            """, draft['id'], channel_id)

            return True

    except Exception as e:
        print(f"❌ Kanal silme hatası: {e}")
        return False


async def get_draft_channels(creator_id: int) -> List[Dict]:
    """Taslağa eklenen kanalları getir"""
    try:
        draft = await get_draft(creator_id)
        if not draft:
            return []

        async with db.pool.acquire() as conn:
            channels = await conn.fetch("""
                SELECT channel_id, channel_username, channel_title
                FROM randy_channels
                WHERE randy_draft_id = $1
                ORDER BY created_at
            """, draft['id'])

            return [dict(c) for c in channels]

    except Exception as e:
        print(f"❌ Kanal listesi hatası: {e}")
        return []


async def clear_draft_channels(creator_id: int) -> bool:
    """Taslaktaki tüm kanalları sil"""
    try:
        draft = await get_draft(creator_id)
        if not draft:
            return False

        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM randy_channels WHERE randy_draft_id = $1
            """, draft['id'])

            return True

    except Exception as e:
        print(f"❌ Kanal temizleme hatası: {e}")
        return False


async def get_randy_channels(randy_id: int) -> List[Dict]:
    """Randy'nin zorunlu kanallarını getir"""
    try:
        async with db.pool.acquire() as conn:
            channels = await conn.fetch("""
                SELECT channel_id, channel_username, channel_title
                FROM randy_channels
                WHERE randy_id = $1
                ORDER BY created_at
            """, randy_id)

            return [dict(c) for c in channels]

    except Exception as e:
        print(f"❌ Randy kanal listesi hatası: {e}")
        return []


# ============================================
# RANDY YÖNETİMİ
# ============================================

async def get_group_draft(group_id: int) -> Optional[Dict[str, Any]]:
    """Grup için hazır taslak var mı kontrol et"""
    try:
        async with db.pool.acquire() as conn:
            draft = await conn.fetchrow("""
                SELECT * FROM randy_drafts
                WHERE group_id = $1
                AND title IS NOT NULL
                AND message IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 1
            """, group_id)

            if draft:
                return dict(draft)
            return None

    except Exception as e:
        print(f"❌ Grup taslağı getirme hatası: {e}")
        return None


async def start_randy(group_id: int, creator_id: int, message_id: int = None) -> Tuple[bool, Optional[Dict]]:
    """
    Randy başlat (taslaktan)

    Args:
        group_id: Grup ID
        creator_id: Başlatan admin ID
        message_id: Telegram mesaj ID (sabitleme için)

    Returns:
        tuple: (Başarılı mı, Randy bilgileri)
    """
    try:
        # Grup için taslak bul
        draft = await get_group_draft(group_id)

        if not draft:
            return False, None

        async with db.pool.acquire() as conn:
            # Aktif Randy var mı kontrol et
            existing = await conn.fetchval("""
                SELECT id FROM randy WHERE group_id = $1 AND status = $2
            """, group_id, STATUS_ACTIVE)

            if existing:
                return False, {"error": "already_active"}

            # Randy oluştur
            randy_id = await conn.fetchval("""
                INSERT INTO randy (
                    group_id, creator_id, title, message, media_type, media_file_id,
                    requirement_type, required_message_count, winner_count,
                    channel_ids, pin_message, status, message_id, started_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
                RETURNING id
            """,
                group_id, creator_id, draft['title'], draft['message'],
                draft.get('media_type', 'none'), draft.get('media_file_id'),
                draft.get('requirement_type', 'none'), draft.get('required_message_count', 0),
                draft.get('winner_count', 1), draft.get('channel_ids'),
                draft.get('pin_message', False), STATUS_ACTIVE, message_id
            )

            # Taslaktaki kanalları Randy'ye taşı
            await conn.execute("""
                UPDATE randy_channels
                SET randy_id = $1, randy_draft_id = NULL
                WHERE randy_draft_id = $2
            """, randy_id, draft['id'])

            # Taslağı sil
            await conn.execute("""
                DELETE FROM randy_drafts WHERE id = $1
            """, draft['id'])

            return True, {
                "id": randy_id,
                "title": draft['title'],
                "message": draft['message'],
                "media_type": draft.get('media_type', 'none'),
                "media_file_id": draft.get('media_file_id'),
                "requirement_type": draft.get('requirement_type', 'none'),
                "required_message_count": draft.get('required_message_count', 0),
                "winner_count": draft.get('winner_count', 1),
                "channel_ids": draft.get('channel_ids'),
                "pin_message": draft.get('pin_message', False)
            }

    except Exception as e:
        print(f"❌ Randy başlatma hatası: {e}")
        return False, None


async def get_active_randy(group_id: int) -> Optional[Dict[str, Any]]:
    """Grupta aktif Randy'yi getir"""
    try:
        async with db.pool.acquire() as conn:
            randy = await conn.fetchrow("""
                SELECT * FROM randy WHERE group_id = $1 AND status = $2
            """, group_id, STATUS_ACTIVE)

            if randy:
                return dict(randy)
            return None

    except Exception as e:
        print(f"❌ Aktif Randy getirme hatası: {e}")
        return None


async def get_randy_by_id(randy_id: int) -> Optional[Dict[str, Any]]:
    """Randy'yi ID ile getir"""
    try:
        async with db.pool.acquire() as conn:
            randy = await conn.fetchrow("""
                SELECT * FROM randy WHERE id = $1
            """, randy_id)

            if randy:
                return dict(randy)
            return None

    except Exception as e:
        print(f"❌ Randy getirme hatası: {e}")
        return None


async def join_randy(
    randy_id: int,
    user_id: int,
    username: str = None,
    first_name: str = None,
    bot = None
) -> Tuple[bool, str]:
    """
    Randy'ye katıl

    Args:
        randy_id: Randy ID
        user_id: Kullanıcı ID
        username: Kullanıcı adı
        first_name: İsim
        bot: Telegram bot instance (kanal üyelik kontrolü için)

    Returns:
        tuple: (Başarılı mı, Mesaj kodu)
    """
    try:
        randy = await get_randy_by_id(randy_id)

        if not randy:
            return False, "bulunamadi"

        if randy['status'] != STATUS_ACTIVE:
            return False, "aktif_degil"

        async with db.pool.acquire() as conn:
            # Zaten katılmış mı?
            existing = await conn.fetchval("""
                SELECT id FROM randy_participants
                WHERE randy_id = $1 AND telegram_id = $2
            """, randy_id, user_id)

            if existing:
                return False, "zaten_katildi"

            # Kanal üyelik kontrolü
            if bot:
                channels = await get_randy_channels(randy_id)
                if channels:
                    not_member_channels = []
                    for channel in channels:
                        try:
                            member = await bot.get_chat_member(channel['channel_id'], user_id)
                            if member.status in ['left', 'kicked']:
                                channel_name = f"@{channel['channel_username']}" if channel['channel_username'] else channel['channel_title']
                                not_member_channels.append(channel_name)
                        except Exception:
                            # Kanal kontrolü başarısız, atla
                            pass

                    if not_member_channels:
                        return False, f"kanal_uyesi_degil:{','.join(not_member_channels)}"

            # Şart kontrolü
            if randy['requirement_type'] != 'none':
                req_type = randy['requirement_type']
                req_count = randy['required_message_count'] or 0

                if req_type == 'post_randy':
                    # Randy sonrası mesaj kontrolü
                    participant = await conn.fetchrow("""
                        SELECT post_randy_message_count FROM randy_participants
                        WHERE randy_id = $1 AND telegram_id = $2
                    """, randy_id, user_id)

                    current_count = participant['post_randy_message_count'] if participant else 0

                    if current_count < req_count:
                        return False, f"post_randy:{req_count}:{current_count}"

                else:
                    # Normal mesaj şartı
                    met, current = await check_message_requirement(
                        user_id, randy['group_id'], req_type, req_count
                    )

                    if not met:
                        return False, f"mesaj_sarti:{req_type}:{req_count}:{current}"

            # Katılımcı ekle
            await conn.execute("""
                INSERT INTO randy_participants (randy_id, telegram_id, username, first_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (randy_id, telegram_id) DO UPDATE
                SET username = COALESCE($3, randy_participants.username),
                    first_name = COALESCE($4, randy_participants.first_name)
            """, randy_id, user_id, username, first_name)

            return True, "basarili"

    except Exception as e:
        print(f"❌ Randy katılım hatası: {e}")
        return False, "hata"


async def get_participant_count(randy_id: int) -> int:
    """Randy katılımcı sayısını getir"""
    try:
        async with db.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM randy_participants
                WHERE randy_id = $1 AND (username IS NOT NULL OR first_name IS NOT NULL)
            """, randy_id)
            return count or 0

    except Exception as e:
        print(f"❌ Katılımcı sayısı hatası: {e}")
        return 0


async def end_randy(randy_id: int) -> Tuple[bool, List[Dict]]:
    """
    Randy'yi sonlandır ve kazananları seç

    Returns:
        tuple: (Başarılı mı, Kazananlar listesi)
    """
    try:
        randy = await get_randy_by_id(randy_id)

        if not randy:
            return False, []

        if randy['status'] != STATUS_ACTIVE:
            return False, []

        async with db.pool.acquire() as conn:
            # Geçerli katılımcıları getir
            participants = await conn.fetch("""
                SELECT telegram_id, username, first_name
                FROM randy_participants
                WHERE randy_id = $1 AND (username IS NOT NULL OR first_name IS NOT NULL)
            """, randy_id)

            participants = [dict(p) for p in participants]

            if len(participants) < randy['winner_count']:
                # Yeterli katılımcı yok
                await conn.execute("""
                    UPDATE randy SET status = $1, ended_at = NOW() WHERE id = $2
                """, STATUS_ENDED, randy_id)
                return True, []

            # Kazananları rastgele seç
            winners = random.sample(participants, randy['winner_count'])

            # Kazananları kaydet
            for winner in winners:
                await conn.execute("""
                    INSERT INTO randy_winners (randy_id, telegram_id, username, first_name)
                    VALUES ($1, $2, $3, $4)
                """, randy_id, winner['telegram_id'], winner.get('username'), winner.get('first_name'))

            # Randy'yi sonlandır
            await conn.execute("""
                UPDATE randy SET status = $1, ended_at = NOW() WHERE id = $2
            """, STATUS_ENDED, randy_id)

            return True, winners

    except Exception as e:
        print(f"❌ Randy sonlandırma hatası: {e}")
        return False, []


async def end_randy_with_count(randy_id: int, winner_count: int) -> Tuple[bool, List[Dict]]:
    """
    Randy'yi belirtilen kazanan sayısıyla sonlandır

    Args:
        randy_id: Randy ID
        winner_count: Kazanan sayısı

    Returns:
        tuple: (Başarılı mı, Kazananlar listesi)
    """
    try:
        randy = await get_randy_by_id(randy_id)

        if not randy:
            return False, []

        if randy['status'] != STATUS_ACTIVE:
            return False, []

        async with db.pool.acquire() as conn:
            # Geçerli katılımcıları getir
            participants = await conn.fetch("""
                SELECT telegram_id, username, first_name
                FROM randy_participants
                WHERE randy_id = $1 AND (username IS NOT NULL OR first_name IS NOT NULL)
            """, randy_id)

            participants = [dict(p) for p in participants]

            if len(participants) == 0:
                # Hiç katılımcı yok
                await conn.execute("""
                    UPDATE randy SET status = $1, ended_at = NOW() WHERE id = $2
                """, STATUS_ENDED, randy_id)
                return True, []

            # Kazanan sayısını katılımcı sayısıyla sınırla
            actual_winner_count = min(winner_count, len(participants))

            # Kazananları rastgele seç
            winners = random.sample(participants, actual_winner_count)

            # Kazananları kaydet
            for winner in winners:
                await conn.execute("""
                    INSERT INTO randy_winners (randy_id, telegram_id, username, first_name)
                    VALUES ($1, $2, $3, $4)
                """, randy_id, winner['telegram_id'], winner.get('username'), winner.get('first_name'))

            # Randy'yi sonlandır
            await conn.execute("""
                UPDATE randy SET status = $1, ended_at = NOW() WHERE id = $2
            """, STATUS_ENDED, randy_id)

            return True, winners

    except Exception as e:
        print(f"❌ Randy sonlandırma hatası (count): {e}")
        return False, []


async def track_post_randy_message(
    group_id: int,
    user_id: int,
    username: str = None,
    first_name: str = None
) -> bool:
    """
    Randy sonrası mesaj takibi

    Args:
        group_id: Grup ID
        user_id: Kullanıcı ID
        username: Username
        first_name: İsim

    Returns:
        bool: Aktif post_randy Randy varsa True
    """
    try:
        async with db.pool.acquire() as conn:
            # Aktif post_randy Randy var mı?
            randy = await conn.fetchrow("""
                SELECT id FROM randy
                WHERE group_id = $1 AND status = $2 AND requirement_type = 'post_randy'
            """, group_id, STATUS_ACTIVE)

            if not randy:
                return False

            # Kullanıcı kaydı var mı? Yoksa oluştur, varsa mesaj sayısını artır
            await conn.execute("""
                INSERT INTO randy_participants (randy_id, telegram_id, username, first_name, post_randy_message_count)
                VALUES ($1, $2, $3, $4, 1)
                ON CONFLICT (randy_id, telegram_id)
                DO UPDATE SET post_randy_message_count = randy_participants.post_randy_message_count + 1
            """, randy['id'], user_id, username, first_name)

            return True

    except Exception as e:
        print(f"❌ Post-Randy mesaj takip hatası: {e}")
        return False


async def update_randy_message_id(randy_id: int, message_id: int) -> bool:
    """Randy mesaj ID'sini güncelle"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE randy SET message_id = $1 WHERE id = $2
            """, message_id, randy_id)
            return True

    except Exception as e:
        print(f"❌ Randy mesaj ID güncelleme hatası: {e}")
        return False


async def get_user_admin_groups(creator_id: int) -> List[Dict]:
    """Kullanıcının admin olduğu grupları getir (bot'un ekli olduğu)"""
    try:
        async with db.pool.acquire() as conn:
            groups = await conn.fetch("""
                SELECT g.group_id, g.title
                FROM telegram_groups g
                JOIN group_admins a ON g.group_id = a.group_id
                WHERE a.user_id = $1 AND a.is_admin = TRUE AND g.is_active = TRUE
            """, creator_id)

            return [dict(g) for g in groups]

    except Exception as e:
        print(f"❌ Admin grupları getirme hatası: {e}")
        return []


async def register_group(group_id: int, title: str) -> bool:
    """Grubu veritabanına kaydet"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO telegram_groups (group_id, title, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (group_id)
                DO UPDATE SET title = $2, is_active = TRUE
            """, group_id, title)
            return True

    except Exception as e:
        print(f"❌ Grup kayıt hatası: {e}")
        return False


async def update_group_admin(group_id: int, user_id: int, is_admin: bool) -> bool:
    """Grup admin kaydını güncelle"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO group_admins (group_id, user_id, is_admin, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (group_id, user_id)
                DO UPDATE SET is_admin = $3, updated_at = NOW()
            """, group_id, user_id, is_admin)
            return True

    except Exception as e:
        print(f"❌ Admin güncelleme hatası: {e}")
        return False

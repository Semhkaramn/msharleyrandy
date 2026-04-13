"""
🗄️ Veritabanı Bağlantısı ve Modeller
Neon.tech PostgreSQL için asyncpg kullanır
"""

import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import DATABASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """PostgreSQL veritabanı yöneticisi"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Veritabanı bağlantı havuzu oluştur"""
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        await self._create_tables()
        logger.info("✅ Veritabanına bağlanıldı")

    async def close(self):
        """Bağlantı havuzunu kapat"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Veritabanı bağlantısı kapatıldı")

    async def _create_tables(self):
        """Tabloları oluştur"""
        async with self.pool.acquire() as conn:
            # Telegram Grupları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_groups (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    title TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Telegram Kullanıcıları (mesaj istatistikleri)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    group_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    message_count INT DEFAULT 0,
                    daily_count INT DEFAULT 0,
                    weekly_count INT DEFAULT 0,
                    monthly_count INT DEFAULT 0,
                    activity_count INT DEFAULT 0,
                    last_message_at TIMESTAMP,
                    last_daily_reset TIMESTAMP DEFAULT NOW(),
                    last_weekly_reset TIMESTAMP DEFAULT NOW(),
                    last_monthly_reset TIMESTAMP DEFAULT NOW(),
                    activity_last_reset TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(telegram_id, group_id)
                )
            """)

            # activity_count ve activity_last_reset kolonlarını ekle (mevcut tablolar için)
            try:
                await conn.execute("ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS activity_count INT DEFAULT 0")
                await conn.execute("ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS activity_last_reset TIMESTAMP DEFAULT NOW()")
            except Exception as e:
                logger.warning(f"⚠️ Kolon ekleme hatası (muhtemelen zaten mevcut): {e}")

            # Grup Adminleri Cache
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS group_admins (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    is_admin BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, user_id)
                )
            """)

            # Randy (Çekiliş) Kayıtları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS randy (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    media_type TEXT DEFAULT 'none',
                    media_file_id TEXT,
                    requirement_type TEXT DEFAULT 'none',
                    required_message_count INT DEFAULT 0,
                    winner_count INT DEFAULT 1,
                    channel_ids TEXT,
                    status TEXT DEFAULT 'draft',
                    message_id BIGINT,
                    pin_message BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Randy Katılımcıları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS randy_participants (
                    id SERIAL PRIMARY KEY,
                    randy_id INT REFERENCES randy(id) ON DELETE CASCADE,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    post_randy_message_count INT DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(randy_id, telegram_id)
                )
            """)

            # Randy Kazananları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS randy_winners (
                    id SERIAL PRIMARY KEY,
                    randy_id INT REFERENCES randy(id) ON DELETE CASCADE,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    won_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Randy Kanalları (Zorunlu takip edilecek kanallar)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS randy_channels (
                    id SERIAL PRIMARY KEY,
                    randy_draft_id INT,
                    randy_id INT,
                    channel_id BIGINT,
                    channel_username TEXT,
                    channel_title TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(randy_draft_id, channel_id),
                    UNIQUE(randy_id, channel_id)
                )
            """)

            # Roll Oturumları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS roll_sessions (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'stopped',
                    active_duration INT DEFAULT 2,
                    current_step INT DEFAULT 0,
                    previous_status TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Roll Adımları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS roll_steps (
                    id SERIAL PRIMARY KEY,
                    session_id INT REFERENCES roll_sessions(id) ON DELETE CASCADE,
                    step_number INT NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(session_id, step_number)
                )
            """)

            # Roll Adım Kullanıcıları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS roll_step_users (
                    id SERIAL PRIMARY KEY,
                    step_id INT REFERENCES roll_steps(id) ON DELETE CASCADE,
                    telegram_user_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    message_count INT DEFAULT 1,
                    last_active TIMESTAMP DEFAULT NOW(),
                    UNIQUE(step_id, telegram_user_id)
                )
            """)

            # Randy Taslakları (özelden ayarlanan ama henüz başlatılmamış)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS randy_drafts (
                    id SERIAL PRIMARY KEY,
                    creator_id BIGINT NOT NULL,
                    group_id BIGINT,
                    title TEXT,
                    message TEXT,
                    media_type TEXT DEFAULT 'none',
                    media_file_id TEXT,
                    requirement_type TEXT DEFAULT 'none',
                    required_message_count INT DEFAULT 0,
                    winner_count INT DEFAULT 1,
                    channel_ids TEXT,
                    pin_message BOOLEAN DEFAULT FALSE,
                    current_step TEXT DEFAULT 'group_select',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Otomatik Etiket Ayarları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_tag_settings (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    interval_minutes INT DEFAULT 60,
                    tag_type TEXT DEFAULT 'naber',
                    start_hour INT DEFAULT 9,
                    end_hour INT DEFAULT 23,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # ============================================
            # ÇEKİLİŞ (GIVEAWAY) TABLOLARI
            # ============================================

            # Çekiliş Ayarları (grup bazlı varsayılan ayarlar)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS giveaway_settings (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    admin_group_id BIGINT,
                    default_duration_hours INT DEFAULT 2,
                    default_winner_count INT DEFAULT 1,
                    max_wins_per_user INT DEFAULT 0,
                    pin_announcement BOOLEAN DEFAULT TRUE,
                    pin_winner_message BOOLEAN DEFAULT TRUE,
                    pin_in_admin_group BOOLEAN DEFAULT TRUE,
                    notify_admin_group BOOLEAN DEFAULT TRUE,
                    winner_message_template TEXT DEFAULT '🎉 Tebrikler! Çekilişi kazandınız!',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Çekilişler
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    prize_text TEXT NOT NULL,
                    duration_hours INT NOT NULL,
                    winner_count INT NOT NULL,
                    max_wins_per_user INT DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    announcement_message_id BIGINT,
                    pin_announcement BOOLEAN DEFAULT TRUE,
                    pin_winner_message BOOLEAN DEFAULT TRUE,
                    notify_admin_group BOOLEAN DEFAULT TRUE,
                    pin_in_admin_group BOOLEAN DEFAULT TRUE,
                    started_at TIMESTAMP DEFAULT NOW(),
                    ends_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Çekiliş Kazanma Zamanları (her kazanan için rastgele belirlenen zaman)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS giveaway_win_times (
                    id SERIAL PRIMARY KEY,
                    giveaway_id INT REFERENCES giveaways(id) ON DELETE CASCADE,
                    win_time TIMESTAMP NOT NULL,
                    slot_number INT NOT NULL,
                    winner_id BIGINT,
                    winner_username TEXT,
                    winner_first_name TEXT,
                    winner_message_id BIGINT,
                    reply_message_id BIGINT,
                    is_won BOOLEAN DEFAULT FALSE,
                    won_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(giveaway_id, slot_number)
                )
            """)

            # Kullanıcı Kazanma Sayıları (limit kontrolü için)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS giveaway_user_wins (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    win_count INT DEFAULT 0,
                    last_win_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, user_id)
                )
            """)

            # ============================================
            # HAFTALIK AKTİVİTE ÖDÜL TABLOLARI
            # ============================================

            # Haftalık Ödül Ayarları (grup bazlı)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_reward_settings (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    top_count INT DEFAULT 5,
                    auto_post_sunday BOOLEAN DEFAULT TRUE,
                    auto_pin BOOLEAN DEFAULT TRUE,
                    post_hour INT DEFAULT 23,
                    post_minute INT DEFAULT 0,
                    last_posted_week INT,
                    last_posted_year INT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Haftalık Ödül Tanımları (sıralama bazlı)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_rewards (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    rank INT NOT NULL,
                    reward_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, rank)
                )
            """)

            # Haftalık Ödül Geçmişi
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_reward_history (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    week_number INT NOT NULL,
                    year INT NOT NULL,
                    rank INT NOT NULL,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    message_count INT NOT NULL,
                    reward_text TEXT,
                    message_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, year, week_number, rank)
                )
            """)

            # İndeksler
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON telegram_users(telegram_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group ON telegram_users(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_status ON randy(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_group ON randy(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_roll_group ON roll_sessions(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_channels_draft ON randy_channels(randy_draft_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_channels_randy ON randy_channels(randy_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_auto_tag_group ON auto_tag_settings(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_giveaway_status ON giveaways(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_giveaway_group ON giveaways(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_giveaway_win_times ON giveaway_win_times(giveaway_id, win_time)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_giveaway_user_wins ON giveaway_user_wins(group_id, user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weekly_reward_settings_group ON weekly_reward_settings(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weekly_rewards_group ON weekly_rewards(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weekly_reward_history ON weekly_reward_history(group_id, year, week_number)")

            logger.info("✅ Tablolar oluşturuldu")


# Singleton instance
db = Database()

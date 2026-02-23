"""
🗄️ Veritabanı Bağlantısı ve Modeller
Neon.tech PostgreSQL için asyncpg kullanır
"""

import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import DATABASE_URL


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
        print("✅ Veritabanına bağlanıldı")

    async def close(self):
        """Bağlantı havuzunu kapat"""
        if self.pool:
            await self.pool.close()
            print("🔌 Veritabanı bağlantısı kapatıldı")

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
                    last_message_at TIMESTAMP,
                    last_daily_reset TIMESTAMP DEFAULT NOW(),
                    last_weekly_reset TIMESTAMP DEFAULT NOW(),
                    last_monthly_reset TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(telegram_id, group_id)
                )
            """)

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

            # İndeksler
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON telegram_users(telegram_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group ON telegram_users(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_status ON randy(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_randy_group ON randy(group_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_roll_group ON roll_sessions(group_id)")

            print("✅ Tablolar oluşturuldu")


# Singleton instance
db = Database()

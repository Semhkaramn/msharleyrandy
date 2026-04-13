"""
🗄️ Migration Manager
Veritabanı şema değişikliklerini yönetir

Kullanım:
    from migrations.migration_manager import MigrationManager
    migration_manager = MigrationManager(db.pool)
    await migration_manager.run_migrations()
"""

import asyncpg
from typing import List, Tuple, Optional
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class Migration:
    """Tek bir migration tanımı"""

    def __init__(self, version: int, name: str, up_sql: str, down_sql: str = ""):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql


class MigrationManager:
    """Veritabanı migration yöneticisi"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.migrations: List[Migration] = []
        self._register_migrations()

    def _register_migrations(self):
        """Tüm migration'ları kaydet"""

        # Migration 001: İlk kurulum - Temel tablolar
        self.migrations.append(Migration(
            version=1,
            name="initial_setup",
            up_sql="""
                -- Telegram Grupları
                CREATE TABLE IF NOT EXISTS telegram_groups (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    title TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- Telegram Kullanıcıları (mesaj istatistikleri)
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
                );

                -- Grup Adminleri Cache
                CREATE TABLE IF NOT EXISTS group_admins (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    is_admin BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, user_id)
                );
            """,
            down_sql="""
                DROP TABLE IF EXISTS group_admins;
                DROP TABLE IF EXISTS telegram_users;
                DROP TABLE IF EXISTS telegram_groups;
            """
        ))

        # Migration 002: Randy tabloları
        self.migrations.append(Migration(
            version=2,
            name="randy_tables",
            up_sql="""
                -- Randy (Çekiliş) Kayıtları
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
                );

                -- Randy Katılımcıları
                CREATE TABLE IF NOT EXISTS randy_participants (
                    id SERIAL PRIMARY KEY,
                    randy_id INT REFERENCES randy(id) ON DELETE CASCADE,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    post_randy_message_count INT DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(randy_id, telegram_id)
                );

                -- Randy Kazananları
                CREATE TABLE IF NOT EXISTS randy_winners (
                    id SERIAL PRIMARY KEY,
                    randy_id INT REFERENCES randy(id) ON DELETE CASCADE,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    won_at TIMESTAMP DEFAULT NOW()
                );

                -- Randy Kanalları (Zorunlu takip edilecek kanallar)
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
                );

                -- Randy Taslakları
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
                );
            """,
            down_sql="""
                DROP TABLE IF EXISTS randy_drafts;
                DROP TABLE IF EXISTS randy_channels;
                DROP TABLE IF EXISTS randy_winners;
                DROP TABLE IF EXISTS randy_participants;
                DROP TABLE IF EXISTS randy;
            """
        ))

        # Migration 003: Roll tabloları
        self.migrations.append(Migration(
            version=3,
            name="roll_tables",
            up_sql="""
                -- Roll Oturumları
                CREATE TABLE IF NOT EXISTS roll_sessions (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'stopped',
                    active_duration INT DEFAULT 2,
                    current_step INT DEFAULT 0,
                    previous_status TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                -- Roll Adımları
                CREATE TABLE IF NOT EXISTS roll_steps (
                    id SERIAL PRIMARY KEY,
                    session_id INT REFERENCES roll_sessions(id) ON DELETE CASCADE,
                    step_number INT NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(session_id, step_number)
                );

                -- Roll Adım Kullanıcıları
                CREATE TABLE IF NOT EXISTS roll_step_users (
                    id SERIAL PRIMARY KEY,
                    step_id INT REFERENCES roll_steps(id) ON DELETE CASCADE,
                    telegram_user_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    message_count INT DEFAULT 1,
                    last_active TIMESTAMP DEFAULT NOW(),
                    UNIQUE(step_id, telegram_user_id)
                );
            """,
            down_sql="""
                DROP TABLE IF EXISTS roll_step_users;
                DROP TABLE IF EXISTS roll_steps;
                DROP TABLE IF EXISTS roll_sessions;
            """
        ))

        # Migration 004: Otomatik etiket ayarları
        self.migrations.append(Migration(
            version=4,
            name="auto_tag_settings",
            up_sql="""
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
                );
            """,
            down_sql="DROP TABLE IF EXISTS auto_tag_settings;"
        ))

        # Migration 005: Çekiliş (Giveaway) tabloları
        self.migrations.append(Migration(
            version=5,
            name="giveaway_tables",
            up_sql="""
                -- Çekiliş Ayarları
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
                );

                -- Çekilişler
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
                );

                -- Çekiliş Kazanma Zamanları
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
                );

                -- Kullanıcı Kazanma Sayıları
                CREATE TABLE IF NOT EXISTS giveaway_user_wins (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    win_count INT DEFAULT 0,
                    last_win_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, user_id)
                );
            """,
            down_sql="""
                DROP TABLE IF EXISTS giveaway_user_wins;
                DROP TABLE IF EXISTS giveaway_win_times;
                DROP TABLE IF EXISTS giveaways;
                DROP TABLE IF EXISTS giveaway_settings;
            """
        ))

        # Migration 006: Haftalık ödül tabloları
        self.migrations.append(Migration(
            version=6,
            name="weekly_reward_tables",
            up_sql="""
                -- Haftalık Ödül Ayarları
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
                );

                -- Haftalık Ödül Tanımları
                CREATE TABLE IF NOT EXISTS weekly_rewards (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    rank INT NOT NULL,
                    reward_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, rank)
                );

                -- Haftalık Ödül Geçmişi
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
                );
            """,
            down_sql="""
                DROP TABLE IF EXISTS weekly_reward_history;
                DROP TABLE IF EXISTS weekly_rewards;
                DROP TABLE IF EXISTS weekly_reward_settings;
            """
        ))

        # Migration 007: Performans indexleri
        self.migrations.append(Migration(
            version=7,
            name="performance_indexes",
            up_sql="""
                -- Temel indexler
                CREATE INDEX IF NOT EXISTS idx_users_telegram ON telegram_users(telegram_id);
                CREATE INDEX IF NOT EXISTS idx_users_group ON telegram_users(group_id);
                CREATE INDEX IF NOT EXISTS idx_telegram_users_group_msg ON telegram_users(group_id, message_count DESC);
                CREATE INDEX IF NOT EXISTS idx_telegram_users_activity ON telegram_users(group_id, activity_count DESC);

                -- Randy indexleri
                CREATE INDEX IF NOT EXISTS idx_randy_status ON randy(status);
                CREATE INDEX IF NOT EXISTS idx_randy_group ON randy(group_id);
                CREATE INDEX IF NOT EXISTS idx_randy_status_group ON randy(status, group_id);
                CREATE INDEX IF NOT EXISTS idx_randy_channels_draft ON randy_channels(randy_draft_id);
                CREATE INDEX IF NOT EXISTS idx_randy_channels_randy ON randy_channels(randy_id);

                -- Roll indexleri
                CREATE INDEX IF NOT EXISTS idx_roll_group ON roll_sessions(group_id);
                CREATE INDEX IF NOT EXISTS idx_roll_sessions_status ON roll_sessions(status, group_id);

                -- Diğer indexler
                CREATE INDEX IF NOT EXISTS idx_auto_tag_group ON auto_tag_settings(group_id);
                CREATE INDEX IF NOT EXISTS idx_giveaway_status ON giveaways(status);
                CREATE INDEX IF NOT EXISTS idx_giveaway_group ON giveaways(group_id);
                CREATE INDEX IF NOT EXISTS idx_giveaway_win_times ON giveaway_win_times(giveaway_id, win_time);
                CREATE INDEX IF NOT EXISTS idx_giveaway_user_wins ON giveaway_user_wins(group_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_weekly_reward_settings_group ON weekly_reward_settings(group_id);
                CREATE INDEX IF NOT EXISTS idx_weekly_rewards_group ON weekly_rewards(group_id);
                CREATE INDEX IF NOT EXISTS idx_weekly_reward_history ON weekly_reward_history(group_id, year, week_number);
            """,
            down_sql="""
                DROP INDEX IF EXISTS idx_users_telegram;
                DROP INDEX IF EXISTS idx_users_group;
                DROP INDEX IF EXISTS idx_telegram_users_group_msg;
                DROP INDEX IF EXISTS idx_telegram_users_activity;
                DROP INDEX IF EXISTS idx_randy_status;
                DROP INDEX IF EXISTS idx_randy_group;
                DROP INDEX IF EXISTS idx_randy_status_group;
                DROP INDEX IF EXISTS idx_randy_channels_draft;
                DROP INDEX IF EXISTS idx_randy_channels_randy;
                DROP INDEX IF EXISTS idx_roll_group;
                DROP INDEX IF EXISTS idx_roll_sessions_status;
                DROP INDEX IF EXISTS idx_auto_tag_group;
                DROP INDEX IF EXISTS idx_giveaway_status;
                DROP INDEX IF EXISTS idx_giveaway_group;
                DROP INDEX IF EXISTS idx_giveaway_win_times;
                DROP INDEX IF EXISTS idx_giveaway_user_wins;
                DROP INDEX IF EXISTS idx_weekly_reward_settings_group;
                DROP INDEX IF EXISTS idx_weekly_rewards_group;
                DROP INDEX IF EXISTS idx_weekly_reward_history;
            """
        ))

        # Migration 008: Etiket Hariç Tutma Tablosu
        self.migrations.append(Migration(
            version=8,
            name="tag_excluded_users",
            up_sql="""
                -- Etiketlenmeyecek Kullanıcılar
                -- Username girilse bile telegram_id olarak kaydedilir
                CREATE TABLE IF NOT EXISTS tag_excluded_users (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    telegram_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    added_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(group_id, telegram_id)
                );

                -- Index
                CREATE INDEX IF NOT EXISTS idx_tag_excluded_group ON tag_excluded_users(group_id);
                CREATE INDEX IF NOT EXISTS idx_tag_excluded_user ON tag_excluded_users(telegram_id);
            """,
            down_sql="DROP TABLE IF EXISTS tag_excluded_users;"
        ))

        # Yeni migration'lar buraya eklenecek...

    async def _ensure_migrations_table(self):
        """Migration takip tablosunu oluştur"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """)

    async def _get_applied_versions(self) -> List[int]:
        """Uygulanmış migration versiyonlarını al"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row['version'] for row in rows]

    async def _apply_migration(self, migration: Migration) -> bool:
        """Tek bir migration uygula"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Migration SQL'ini çalıştır
                    await conn.execute(migration.up_sql)

                    # Migration kaydını ekle
                    await conn.execute(
                        """
                        INSERT INTO schema_migrations (version, name, applied_at)
                        VALUES ($1, $2, $3)
                        """,
                        migration.version,
                        migration.name,
                        datetime.now()
                    )
            return True
        except Exception as e:
            logger.error(f"❌ Migration {migration.version} ({migration.name}) hatası: {e}")
            return False

    async def _rollback_migration(self, migration: Migration) -> bool:
        """Tek bir migration'ı geri al"""
        if not migration.down_sql:
            logger.warning(f"⚠️ Migration {migration.version} için rollback SQL yok")
            return False

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Rollback SQL'ini çalıştır
                    await conn.execute(migration.down_sql)

                    # Migration kaydını sil
                    await conn.execute(
                        "DELETE FROM schema_migrations WHERE version = $1",
                        migration.version
                    )
            return True
        except Exception as e:
            logger.error(f"❌ Rollback {migration.version} hatası: {e}")
            return False

    async def run_migrations(self) -> Tuple[int, int]:
        """
        Bekleyen tüm migration'ları çalıştır

        Returns:
            (applied_count, total_pending) tuple
        """
        await self._ensure_migrations_table()
        applied_versions = await self._get_applied_versions()

        pending = [m for m in self.migrations if m.version not in applied_versions]
        pending.sort(key=lambda m: m.version)

        applied_count = 0
        for migration in pending:
            logger.info(f"🔄 Migration {migration.version}: {migration.name} uygulanıyor...")
            if await self._apply_migration(migration):
                logger.info(f"✅ Migration {migration.version} başarılı")
                applied_count += 1
            else:
                logger.error(f"❌ Migration {migration.version} başarısız, durduruluyor")
                break

        return applied_count, len(pending)

    async def rollback(self, target_version: Optional[int] = None) -> int:
        """
        Migration'ları geri al

        Args:
            target_version: Hedef versiyon (None ise son migration geri alınır)

        Returns:
            Geri alınan migration sayısı
        """
        applied_versions = await self._get_applied_versions()
        if not applied_versions:
            logger.info("ℹ️ Geri alınacak migration yok")
            return 0

        if target_version is None:
            target_version = max(applied_versions) - 1

        to_rollback = [m for m in self.migrations
                       if m.version in applied_versions and m.version > target_version]
        to_rollback.sort(key=lambda m: m.version, reverse=True)

        rolled_back = 0
        for migration in to_rollback:
            logger.info(f"🔙 Migration {migration.version}: {migration.name} geri alınıyor...")
            if await self._rollback_migration(migration):
                logger.info(f"✅ Rollback {migration.version} başarılı")
                rolled_back += 1
            else:
                break

        return rolled_back

    async def get_status(self) -> dict:
        """Migration durumunu al"""
        await self._ensure_migrations_table()
        applied_versions = await self._get_applied_versions()

        return {
            "current_version": max(applied_versions) if applied_versions else 0,
            "applied_count": len(applied_versions),
            "total_migrations": len(self.migrations),
            "pending_count": len([m for m in self.migrations if m.version not in applied_versions]),
            "applied_versions": applied_versions
        }

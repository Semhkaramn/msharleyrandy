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

        # Migration 001: İlk kurulum (mevcut tablolar)
        self.migrations.append(Migration(
            version=1,
            name="initial_setup",
            up_sql="""
                -- Bu migration mevcut tabloları temsil eder
                -- Yeni bir kurulumda otomatik çalışır
                SELECT 1;
            """,
            down_sql=""
        ))

        # Migration 002: Activity kolonları
        self.migrations.append(Migration(
            version=2,
            name="add_activity_columns",
            up_sql="""
                ALTER TABLE telegram_users
                ADD COLUMN IF NOT EXISTS activity_count INT DEFAULT 0;

                ALTER TABLE telegram_users
                ADD COLUMN IF NOT EXISTS activity_last_reset TIMESTAMP DEFAULT NOW();
            """,
            down_sql="""
                ALTER TABLE telegram_users DROP COLUMN IF EXISTS activity_count;
                ALTER TABLE telegram_users DROP COLUMN IF EXISTS activity_last_reset;
            """
        ))

        # Migration 003: Index optimizasyonları
        self.migrations.append(Migration(
            version=3,
            name="add_performance_indexes",
            up_sql="""
                -- Telegram users için index
                CREATE INDEX IF NOT EXISTS idx_telegram_users_group_msg
                ON telegram_users(group_id, message_count DESC);

                CREATE INDEX IF NOT EXISTS idx_telegram_users_activity
                ON telegram_users(group_id, activity_count DESC);

                -- Randy için index
                CREATE INDEX IF NOT EXISTS idx_randy_status
                ON randy(status, group_id);

                -- Roll sessions için index
                CREATE INDEX IF NOT EXISTS idx_roll_sessions_status
                ON roll_sessions(status, group_id);
            """,
            down_sql="""
                DROP INDEX IF EXISTS idx_telegram_users_group_msg;
                DROP INDEX IF EXISTS idx_telegram_users_activity;
                DROP INDEX IF EXISTS idx_randy_status;
                DROP INDEX IF EXISTS idx_roll_sessions_status;
            """
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
            print(f"❌ Migration {migration.version} ({migration.name}) hatası: {e}")
            return False

    async def _rollback_migration(self, migration: Migration) -> bool:
        """Tek bir migration'ı geri al"""
        if not migration.down_sql:
            print(f"⚠️ Migration {migration.version} için rollback SQL yok")
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
            print(f"❌ Rollback {migration.version} hatası: {e}")
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
            print(f"🔄 Migration {migration.version}: {migration.name} uygulanıyor...")
            if await self._apply_migration(migration):
                print(f"✅ Migration {migration.version} başarılı")
                applied_count += 1
            else:
                print(f"❌ Migration {migration.version} başarısız, durduruluyor")
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
            print("ℹ️ Geri alınacak migration yok")
            return 0

        if target_version is None:
            target_version = max(applied_versions) - 1

        to_rollback = [m for m in self.migrations
                       if m.version in applied_versions and m.version > target_version]
        to_rollback.sort(key=lambda m: m.version, reverse=True)

        rolled_back = 0
        for migration in to_rollback:
            print(f"🔙 Migration {migration.version}: {migration.name} geri alınıyor...")
            if await self._rollback_migration(migration):
                print(f"✅ Rollback {migration.version} başarılı")
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

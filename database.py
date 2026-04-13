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
from enums import (
    RandyStatus,
    RollStatus,
    MemberStatus,
    RequirementType,
    MediaType,
    GiveawayStatus
)

logger = get_logger(__name__)


class Database:
    """PostgreSQL veritabanı yöneticisi"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._migration_manager = None

    async def connect(self):
        """Veritabanı bağlantı havuzu oluştur"""
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )

        # Migration manager'ı başlat ve migration'ları çalıştır
        await self._run_migrations()

        logger.info("✅ Veritabanına bağlanıldı")

    async def _run_migrations(self):
        """Migration'ları çalıştır"""
        from migrations.migration_manager import MigrationManager

        self._migration_manager = MigrationManager(self.pool)

        # Migration durumunu kontrol et
        status = await self._migration_manager.get_status()
        logger.info(f"📊 Migration durumu: {status['applied_count']}/{status['total_migrations']} uygulandı")

        if status['pending_count'] > 0:
            logger.info(f"🔄 {status['pending_count']} bekleyen migration uygulanıyor...")
            applied, total = await self._migration_manager.run_migrations()
            if applied > 0:
                logger.info(f"✅ {applied} migration başarıyla uygulandı")
            elif total > 0:
                logger.warning(f"⚠️ Migration'lar uygulanamadı")

    async def close(self):
        """Bağlantı havuzunu kapat"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Veritabanı bağlantısı kapatıldı")

    async def get_migration_status(self) -> Optional[dict]:
        """Migration durumunu döndür"""
        if self._migration_manager:
            return await self._migration_manager.get_status()
        return None

    async def rollback_migration(self, target_version: Optional[int] = None) -> int:
        """Migration'ları geri al"""
        if self._migration_manager:
            return await self._migration_manager.rollback(target_version)
        return 0


# Singleton instance
db = Database()

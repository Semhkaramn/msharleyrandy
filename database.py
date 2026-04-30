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
        self._connected = False

    async def connect(self):
        """Veritabanı bağlantı havuzu oluştur"""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,  # Minimum bağlantı - daha hızlı başlangıç
                max_size=5,  # Heroku için optimize
                command_timeout=30,  # 30 saniye timeout
                timeout=10,  # Bağlantı timeout'u
                statement_cache_size=0  # Neon.tech için cache kapalı
            )

            self._connected = True

            # Migration manager'ı başlat ve migration'ları çalıştır
            await self._run_migrations()

            logger.info("✅ Veritabanına bağlanıldı")

        except Exception as e:
            logger.error(f"❌ Veritabanı bağlantı hatası: {e}")
            raise

    async def _run_migrations(self):
        """Migration'ları çalıştır"""
        from migrations.migration_manager import MigrationManager

        try:
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
        except Exception as e:
            logger.warning(f"⚠️ Migration hatası (devam ediliyor): {e}")

    async def close(self):
        """Bağlantı havuzunu kapat"""
        if self.pool:
            try:
                await asyncio.wait_for(self.pool.close(), timeout=5.0)
                self._connected = False
                logger.info("🔌 Veritabanı bağlantısı kapatıldı")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Veritabanı kapatma timeout")
            except Exception as e:
                logger.error(f"❌ Veritabanı kapatma hatası: {e}")

    @property
    def is_connected(self) -> bool:
        """Bağlantı durumunu döndür"""
        return self._connected and self.pool is not None

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

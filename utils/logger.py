"""
📝 Logging Sistemi
Merkezi log yönetimi - print() yerine kullanılır
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "msharleyrandy",
    level: int = logging.INFO,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Logger oluştur ve yapılandır

    Args:
        name: Logger adı
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Özel log formatı (None ise varsayılan kullanılır)

    Returns:
        Yapılandırılmış logger instance
    """
    if log_format is None:
        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    # Root logger'ı yapılandır
    logger = logging.getLogger(name)

    # Daha önce handler eklenmemişse ekle
    if not logger.handlers:
        logger.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Modül için logger al

    Args:
        module_name: Modül adı (genellikle __name__)

    Returns:
        Logger instance

    Kullanım:
        from utils.logger import get_logger
        logger = get_logger(__name__)

        logger.info("✅ Başarılı")
        logger.error("❌ Hata: %s", error_message)
        logger.warning("⚠️ Uyarı")
        logger.debug("🔍 Debug bilgisi")
    """
    # Ana logger'ın altında child logger oluştur
    return logging.getLogger(f"msharleyrandy.{module_name}")


# Uygulamanın başında bir kez çağrılacak
_root_logger = setup_logger()


# Kısayol fonksiyonları (geriye uyumluluk için)
def log_info(message: str) -> None:
    """Info log - print(f"✅ ...") yerine"""
    _root_logger.info(message)


def log_error(message: str) -> None:
    """Error log - print(f"❌ ...") yerine"""
    _root_logger.error(message)


def log_warning(message: str) -> None:
    """Warning log - print(f"⚠️ ...") yerine"""
    _root_logger.warning(message)


def log_debug(message: str) -> None:
    """Debug log"""
    _root_logger.debug(message)


def log_exception(message: str, exc: Exception) -> None:
    """Exception log - hata detayları ile birlikte"""
    _root_logger.exception(f"{message}: {exc}")

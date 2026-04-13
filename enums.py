"""
🔢 Enum Tanımları
Magic string'ler yerine type-safe enum kullanımı
"""

from enum import Enum


class RandyStatus(str, Enum):
    """Randy çekiliş durumları"""
    DRAFT = 'draft'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class RollStatus(str, Enum):
    """Roll oturumu durumları"""
    STOPPED = 'stopped'
    ACTIVE = 'active'
    PAUSED = 'paused'
    BREAK = 'break'
    LOCKED = 'locked'
    LOCKED_BREAK = 'locked_break'


class MemberStatus(str, Enum):
    """Telegram üyelik durumları"""
    LEFT = 'left'
    KICKED = 'kicked'
    BANNED = 'banned'
    MEMBER = 'member'
    ADMINISTRATOR = 'administrator'
    CREATOR = 'creator'
    RESTRICTED = 'restricted'

    @classmethod
    def left_statuses(cls) -> list:
        """Gruptan ayrılanların durumları"""
        return [cls.LEFT.value, cls.KICKED.value, cls.BANNED.value]

    @classmethod
    def member_statuses(cls) -> list:
        """Aktif üye durumları"""
        return [cls.MEMBER.value, cls.ADMINISTRATOR.value, cls.CREATOR.value, cls.RESTRICTED.value]


class RequirementType(str, Enum):
    """Randy mesaj şartı tipleri"""
    NONE = 'none'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    ALL_TIME = 'all_time'
    POST_RANDY = 'post_randy'

    @property
    def display_name(self) -> str:
        """Türkçe görüntüleme adı"""
        names = {
            'none': 'Şartsız',
            'daily': 'Günlük Mesaj',
            'weekly': 'Haftalık Mesaj',
            'monthly': 'Aylık Mesaj',
            'all_time': 'Toplam Mesaj',
            'post_randy': 'Randy Sonrası Mesaj'
        }
        return names.get(self.value, self.value)


class MediaType(str, Enum):
    """Medya tipleri"""
    NONE = 'none'
    PHOTO = 'photo'
    VIDEO = 'video'
    ANIMATION = 'animation'

    @property
    def display_name(self) -> str:
        """Türkçe görüntüleme adı"""
        names = {
            'none': 'Sadece Metin',
            'photo': 'Fotoğraf',
            'video': 'Video',
            'animation': 'GIF/Animasyon'
        }
        return names.get(self.value, self.value)


class GiveawayStatus(str, Enum):
    """Çekiliş durumları"""
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


# Roll durumu emoji eşleşmeleri
ROLL_STATUS_EMOJI = {
    RollStatus.STOPPED: '🔴 Durduruldu',
    RollStatus.ACTIVE: '🟢 Aktif',
    RollStatus.PAUSED: '🟡 Duraklatıldı',
    RollStatus.BREAK: '☕ Mola',
    RollStatus.LOCKED: '🔒 Kilitli',
    RollStatus.LOCKED_BREAK: '🔒☕ Kilitli Mola',
}

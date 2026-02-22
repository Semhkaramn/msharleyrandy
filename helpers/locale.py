TEXTS = {
    "start": "Merhaba! Ben bir cekilis botuyum. Grubunuza ekleyin ve /randy komutuyla cekilis baslatin!",
    "help": """Komutlar:
/randy - Yeni cekilis baslat
/number [sayi] - Kazanan sayisini ayarla
/subscribe [kanal] - Abonelik sarti ekle
/nosubscribe - Abonelik sartini kaldir
/rafflemessage - Cekilis mesajini ayarla
/winnermessage - Kazanan mesajini ayarla
/nodelete - Mesaj silmeyi ac/kapat
/setminmessage [sayi] [donem] - Minimum mesaj sarti ayarla
/stats - Grup istatistikleri
/mymessages - Mesaj sayinizi gorun""",
    "only_admin": "Bu komutu sadece yoneticiler kullanabilir.",
    "only_group": "Bu komut sadece gruplarda calisir.",
    "raffle_started": "Cekilis basladi! Katilmak icin asagidaki butona tiklayin.",
    "participate": "Katil",
    "already_participated": "Zaten katildiniz!",
    "participated": "Cekilise katildiniz!",
    "not_subscribed": "Oncelikle {channel} kanalina abone olmaniz gerekiyor.",
    "min_message_required": "Katilmak icin {period} en az {count} mesaj atmis olmaniz gerekiyor. Simdilik {current} mesajiniz var.",
    "raffle_ended": "Cekilis sona erdi!",
    "winners": "Kazananlar:",
    "no_participants": "Katilimci yok!",
    "number_set": "Kazanan sayisi {number} olarak ayarlandi.",
    "subscribe_set": "Abonelik sarti eklendi: {channel}",
    "subscribe_removed": "Abonelik sarti kaldirildi.",
    "nodelete_on": "Mesaj silme kapatildi.",
    "nodelete_off": "Mesaj silme acildi.",
    "min_message_set": "Minimum mesaj sarti: {count} mesaj ({period})",
    "min_message_removed": "Minimum mesaj sarti kaldirildi.",
    "your_messages": "Mesaj sayiniz ({period}): {count}",
    "raffle_message_set": "Cekilis mesaji ayarlandi.",
    "winner_message_set": "Kazanan mesaji ayarlandi.",
    "stats": """Grup Istatistikleri:
Kazanan sayisi: {number}
Abonelik sarti: {subscribe}
Mesaj silme: {nodelete}
Min. mesaj: {min_message} ({period})""",
    "not_allowed": "Bu bot bu grupta calismiyor."
}

def get_text(key: str, **kwargs) -> str:
    text = TEXTS.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

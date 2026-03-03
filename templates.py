"""
📝 Mesaj Taslakları
Tüm bot mesajları burada merkezi olarak tutulur
"""

# ============================================
# 🏠 ANA MENÜ
# ============================================

MENU = {
    "ANA_MENU": (
        "🎰 <b>Randy & Roll Bot</b>\n\n"
        "Merhaba! Ne yapmak istersiniz?\n\n"
        "Aşağıdaki butonlardan birini seçin:"
    ),

    "RANDY_MENU": (
        "🎲 <b>Randy Yönetimi</b>\n\n"
        "Randy (çekiliş) ayarlarını buradan yapabilirsiniz.\n"
        "Ayarlar kalıcıdır - bir kez ayarlayın, sürekli kullanın."
    ),

    "RANDY_OLUSTUR": "🆕 <b>Randy Ayarları</b>\n\nAşağıdaki ayarları yapabilirsiniz:",

    "RANDY_OLUSTUR_START": "🆕 <b>Yeni Randy Oluştur</b>\n\nAşağıdaki adımları takip edin:\n\n📍 Randy'nin açılacağı grubu seçin:",

    "GRUP_SEC": "📍 <b>Grup Seçimi</b>\n\nRandy'nin açılacağı grubu seçin:\n\n<i>Not: Sadece admin olduğunuz gruplar listelenir.</i>",

    "GRUP_BULUNAMADI": "❌ Admin olduğunuz grup bulunamadı.\n\nBotu gruba ekleyip admin yapın.",

    "MESAJ_AYARLA": "✏️ <b>Randy Mesajı</b>\n\n{current_value}Randy mesajını yazın:\n\n<i>Şu anda mesaj gönderin:</i>",

    "SART_SEC": "📋 <b>Katılım Şartı</b>\n\n{current_value}Katılım için gerekli şartı seçin:",

    "MESAJ_SAYISI_GIR": "🔢 <b>Mesaj Sayısı</b>\n\n{current_value}Gerekli mesaj sayısını girin:\n\n<i>Örnek: 50</i>",

    "KANAL_EKLE": "📢 <b>Zorunlu Kanallar</b>\n\nKatılım için üye olunması gereken kanal ID'lerini girin.\n\n<i>Virgülle ayırın. Örnek:</i>\n<code>-1001234567890,-1009876543210</code>\n\n<i>Boş bırakmak için 'geç' yazın.</i>",

    "KAZANAN_SAYISI": "🏆 <b>Kazanan Sayısı</b>\n\n{current_value}Kaç kişi kazanacak? Sayı yazın:\n\n<i>Örnek: 3</i>",

    "MEDYA_SEC": "🖼️ <b>Medya Seçimi</b>\n\nRandy mesajına medya eklemek ister misiniz?",

    "MEDYA_GONDER": "📤 <b>Medya Ekle</b>\n\n{current_value}Fotoğraf, video veya GIF gönderin.\n\n<i>Medya eklemek istemiyorsanız 'Geri' butonuna tıklayın.</i>",

    "ONIZLEME": "👁️ <b>Randy Önizleme</b>\n\n{preview}\n\n<b>Ayarlar:</b>\n• Grup: {group}\n• Şart: {requirement}\n• Kazanan: {winners} kişi\n• Medya: {media}\n• Sabitle: {pin}",

    "RANDY_KAYDEDILDI": "✅ Randy taslağı kaydedildi!\n\nGrupta <code>/randy</code> yazarak başlatabilirsiniz.",

    "SABITLE_SEC": "📌 <b>Mesaj Sabitleme</b>\n\nRandy mesajı sabitlensin mi?",

    # Roll Menüsü
    "ROLL_MENU": (
        "🎯 <b>Roll Yönetimi</b>\n\n"
        "Roll sistemi, kullanıcıların aktiflik takibini yapar.\n"
        "Belirli süre içinde mesaj yazmayanlar listeden çıkarılır.\n\n"
        "<b>📝 Kullanılabilir Komutlar:</b>\n\n"
        "• <code>roll X</code> - Roll başlat (X dakika)\n"
        "• <code>roll adım</code> - Adım kaydet\n"
        "• <code>roll mola</code> - Mola başlat\n"
        "• <code>roll devam</code> - Moladan devam et\n"
        "• <code>roll kilit</code> - Yeni kullanıcı girişini kapat\n"
        "• <code>roll aç</code> - Kilidi aç\n"
        "• <code>roll bitir</code> - Roll'u sonlandır\n"
        "• <code>liste</code> - Mevcut listeyi göster\n\n"
        "<b>⚙️ Nasıl Çalışır:</b>\n"
        "1. <code>roll 2</code> yazarak başlatın (2 dk kuralı)\n"
        "2. Kullanıcılar mesaj attıkça listeye eklenir\n"
        "3. X dakika yazmayanlar otomatik silinir\n"
        "4. <code>roll adım</code> ile mevcut adımı kaydedin\n"
        "5. <code>roll devam</code> ile yeni adıma geçin\n"
        "6. <code>roll bitir</code> ile sonlandırın"
    ),

    # Etiket Menüsü
    "ETIKET_MENU": (
        "🏷️ <b>Etiket Yönetimi</b>\n\n"
        "Gruptaki kullanıcıları toplu olarak etiketleyin.\n\n"
        "<b>📝 Kullanılabilir Komutlar (Grupta):</b>\n\n"
        "• <code>/etiket</code> - Varsayılan mesajla etiketle\n"
        "• <code>/etiket [mesaj]</code> - Özel mesajla etiketle\n"
        "• <code>/etiket [emoji] [mesaj]</code> - Premium emoji ile etiketle\n"
        "• <code>/naber</code> - Rastgele mesajlarla tek tek etiketle\n"
        "• <code>/dur</code> - Aktif etiketlemeyi durdur\n\n"
        "<b>⚙️ Nasıl Çalışır:</b>\n"
        "• Kullanıcılar 5'erli gruplar halinde etiketlenir\n"
        "• Premium emoji kullanmak için mesajın başına ekleyin\n"
        "• Örnek: <code>/etiket 💎 Merhaba!</code>\n\n"
        "<b>💎 Premium Emoji Desteği:</b>\n"
        "Premium hesabınızla özel emoji kullanabilirsiniz.\n"
        "Bot, gönderdiğiniz premium emojiyi otomatik algılar."
    ),

    # GPT Menüsü
    "GPT_MENU": (
        "🤖 <b>GPT Harley Ayarları</b>\n\n"
        "Harley'nin GPT ile sohbet etmesini açıp kapatabilirsiniz.\n\n"
        "<b>Açık olduğunda:</b>\n"
        "• Mesajda 'harley' yazınca cevap verir\n"
        "• Bot mesajına reply yapınca cevap verir\n\n"
        "<b>Harley'nin Karakteri:</b>\n"
        "• Tatlı, cilveli ve sevecen bir kız 💕\n"
        "• Cana yakın ve samimi\n"
        "• Kısa ve tatlı cevaplar verir\n\n"
        "Bir gruba tıklayarak durumu değiştirin:"
    ),

    # İstatistikler Menüsü
    "STATS_MENU": (
        "📊 <b>İstatistikler</b>\n\n"
        "Grup istatistiklerini görüntüleyin.\n\n"
        "<b>📝 Kullanılabilir Komutlar (Grupta):</b>\n\n"
        "<b>Herkes:</b>\n"
        "• <code>.ben</code> - Kendi istatistikleriniz\n\n"
        "<b>Adminler:</b>\n"
        "• <code>.bilgi</code> (reply) - Birinin istatistikleri\n"
        "• <code>.bilgi @username</code> - Kullanıcı istatistikleri\n"
        "• <code>.günlük</code> - Günlük sıralama\n"
        "• <code>.haftalık</code> - Haftalık sıralama\n"
        "• <code>.aylık</code> - Aylık sıralama\n\n"
        "<i>Bu komutları grupta kullanabilirsiniz.</i>"
    ),
}

# ============================================
# 🎲 RANDY MESAJLARI
# ============================================

RANDY = {
    "KATIL_BUTONU": "🎉 Katıl",

    "BASARIYLA_KATILDIN": "🎉 Başarıyla katıldınız!",
    "ZATEN_KATILDIN": "✅ Zaten katıldınız!",
    "BULUNAMADI": "❌ Randy bulunamadı.",
    "AKTIF_DEGIL": "❌ Bu Randy artık aktif değil.",
    "YASAKLI": "🚫 Yasaklısınız ve Randy'lere katılamazsınız.",

    "KANAL_UYESI_DEGIL": "❌ Önce şu kanallara üye olmalısınız:\n{channels}",

    "MESAJ_SARTI_KARSILANMADI": "❌ {period} en az {required} mesaj yazmalısınız.\n\n📊 Şu anki mesajınız: {current}",

    "POST_RANDY_SARTI": "❌ Randy başladıktan sonra {required} mesaj yazmalısınız.\n\n📊 Şu anki mesajınız: {current}",

    "GRUP_ADMINI_DEGIL": "❌ Bu grubun admini değilsiniz.",

    "TASLAK_YOK": "❌ Bu grup için hazır Randy taslağı yok.\n\nÖnce özelden /start ile taslak oluşturun.",

    "BASLADI": "🎉 <b>RANDY BAŞLADI!</b>\n\n{message}\n\n{channels_text}👥 Katılımcı: {participants}\n🏆 Kazanan: {winners} kişi",

    "BASLADI_SARTLI": "🎉 <b>RANDY BAŞLADI!</b>\n\n{message}\n\n📋 <b>Şart:</b> {requirement}\n{channels_text}👥 Katılımcı: {participants}\n🏆 Kazanan: {winners} kişi",

    "BITTI": "🎊 <b>RANDY SONA ERDİ!</b>\n\n👥 Toplam Katılımcı: {participants}\n\n🏆 <b>Kazananlar:</b>\n{winner_list}\n\nTebrikler!",

    "BITTI_KATILIMCI_AZ": "🎊 <b>RANDY SONA ERDİ!</b>\n\n👥 Toplam Katılımcı: {participants}\n⚠️ Katılımcı sayısı ({participants}) kazanan sayısından ({winner_count}) az olduğu için tüm katılımcılar kazandı!\n\n🏆 <b>Kazananlar:</b>\n{winner_list}\n\nTebrikler!",

    "KAZANAN_YOK": "😔 Yeterli katılımcı olmadığı için kazanan belirlenemedi.",

    "ZATEN_AKTIF": "⚠️ Bu grupta zaten aktif bir Randy var.",
}

# ============================================
# 🎲 ROLL MESAJLARI
# ============================================

ROLL = {
    "BASLADI": "✅ Roll Başladı!\n⏳ {duration} dakika içinde mesaj yazmayan listeden çıkarılır.",

    "ADIM_KAYDEDILDI": "📌 Adım {step} Kaydedildi!\n\n{list}",

    "MOLA_BASLADI": "☕ Mola başladı.\n<code>roll devam</code> ile devam edilebilir.",
    "MOLA_BASLADI_KILITLI": "☕🔒 Mola başladı (kilit aktif).\n<code>roll devam</code> ile devam edilebilir.",
    "ZATEN_MOLADA": "⚠️ Zaten molada.",
    "MOLA_YOK": "⚠️ Mola veya duraklama yok.",

    "DEVAM_EDIYOR": "✅ Roll devam ediyor!\n⏳ {duration} dakika içinde mesaj yazmayan listeden çıkarılır.",
    "DEVAM_EDIYOR_KILITLI": "✅🔒 Roll devam ediyor (kilit aktif)!\n⏳ {duration} dakika içinde mesaj yazmayan listeden çıkarılır.",

    "KILITLENDI": "🔒 Roll kilitlendi.\nArtık yeni kullanıcı eklenmiyor.",
    "KILITLENDI_MOLADA": "🔒☕ Roll kilitlendi (mola devam ediyor).\nArtık yeni kullanıcı eklenmiyor.",
    "KILIT_ACILDI": "🔓 Roll kilidi açıldı.",
    "ZATEN_KILITLI": "⚠️ Roll zaten kilitli.",
    "KILITLI_DEGIL": "⚠️ Roll kilitli değil.",

    "SONLANDIRILDI": "🏁 Roll sonlandırıldı!\n\n{list}",

    "AKTIF_DEGIL": "⚠️ Roll aktif değil.",
    "ZATEN_DURDURULMUS": "⚠️ Roll zaten durdurulmuş.",

    "LISTE_BOS": "📭 Henüz kullanıcı yok.",
    "KULLANICI_YOK": "📭 Kaydedilecek aktif kullanıcı yok.",

    "DURUM": "📊 Roll Durumu: {status}\n⏳ {duration} dakika kuralı\n\n{list}",
}

# ============================================
# 📊 İSTATİSTİK MESAJLARI
# ============================================

STATS = {
    "ME": "📊 <b>{name} - Mesaj İstatistiklerin</b>\n\n📅 <b>Bugün:</b> {daily} mesaj\n📆 <b>Bu Hafta:</b> {weekly} mesaj\n🗓️ <b>Bu Ay:</b> {monthly} mesaj\n📈 <b>Toplam:</b> {total} mesaj",

    "GUNLUK": "📅 <b>{name}</b> bugün <b>{count}</b> mesaj yazdı.",
    "HAFTALIK": "📆 <b>{name}</b> bu hafta <b>{count}</b> mesaj yazdı.",
    "AYLIK": "🗓️ <b>{name}</b> bu ay <b>{count}</b> mesaj yazdı.",

    "KAYIT_YOK": "📭 Henüz mesaj istatistiğiniz yok. Grupta mesaj yazın!",

    # Gelişmiş istatistik kartı
    "USER_CARD": (
        "╔══════════════════════╗\n"
        "║  📊 <b>İSTATİSTİK KARTI</b>  ║\n"
        "╠══════════════════════╣\n"
        "║ 👤 <b>{name}</b>\n"
        "{username_line}"
        "╠══════════════════════╣\n"
        "║ 💬 <b>MESAJ İSTATİSTİKLERİ</b>\n"
        "╟──────────────────────╢\n"
        "║ 📅 Bugün      ➜ <b>{daily}</b>\n"
        "║ 📆 Bu Hafta   ➜ <b>{weekly}</b>\n"
        "║ 🗓 Bu Ay      ➜ <b>{monthly}</b>\n"
        "║ 📈 Toplam     ➜ <b>{total}</b>\n"
        "╠══════════════════════╣\n"
        "║ 🎲 <b>RANDY İSTATİSTİKLERİ</b>\n"
        "╟──────────────────────╢\n"
        "║ 🎫 Katılım    ➜ <b>{randy_participated}</b>\n"
        "║ 🏆 Kazanma    ➜ <b>{randy_won}</b>\n"
        "{win_rate_line}"
        "╚══════════════════════╝"
    ),

    # Bot başlatma mesajı
    "BOT_BASLAT": (
        "👋 Hey {mention}!\n\n"
        "📊 İstatistiklerini görmek için önce botu başlatman gerekiyor.\n\n"
        "👇 Aşağıdaki butona tıkla ve ardından <b>\"Başlattım\"</b> butonuna bas:"
    ),
}

# ============================================
# 🔘 BUTON METİNLERİ
# ============================================

BUTTONS = {
    # Ana Menü
    "RANDY_YONETIMI": "🎲 Randy Yönetimi",
    "ROLL_YONETIMI": "🎯 Roll Yönetimi",
    "ETIKET_YONETIMI": "🏷️ Etiket Yönetimi",
    "GPT_AYARLARI": "🤖 GPT Harley",
    "ISTATISTIKLER": "📊 İstatistikler",
    "AYARLAR": "⚙️ Ayarlar",

    # Randy Menü
    "YENI_RANDY": "🆕 Yeni Randy Oluştur",
    "AKTIF_RANDYLER": "📋 Aktif Randy'ler",
    "GECMIS": "📜 Geçmiş",
    "RANDY_AYARLARI": "⚙️ Randy Ayarları",

    # Randy Oluşturma
    "MESAJ_AYARLA": "✏️ Mesajı Ayarla",
    "SART_AYARLA": "📋 Şart Ayarla",
    "KAZANAN_AYARLA": "🏆 Kazanan Sayısı",
    "MEDYA_EKLE": "🖼️ Medya Ekle",
    "KANAL_EKLE": "📢 Kanal Ekle",
    "SABITLE": "📌 Sabitle",
    "ONIZLE": "👁️ Önizle",
    "KAYDET": "💾 Kaydet",

    # Şartlar
    "SARTSIZ": "✅ Şartsız",
    "GUNLUK_MESAJ": "📅 Günlük Mesaj",
    "HAFTALIK_MESAJ": "📆 Haftalık Mesaj",
    "AYLIK_MESAJ": "🗓️ Aylık Mesaj",
    "TOPLAM_MESAJ": "📈 Toplam Mesaj",
    "RANDY_SONRASI": "🎲 Randy Sonrası Mesaj",

    # Medya
    "SADECE_METIN": "📝 Sadece Metin",
    "FOTOGRAF": "📷 Fotoğraf",
    "VIDEO": "🎬 Video",
    "GIF": "🎞️ GIF",

    # Genel
    "GERI": "◀️ Geri",
    "ANA_MENU": "🏠 Ana Menü",
    "IPTAL": "❌ Kapat",
    "EVET": "✅ Evet",
    "HAYIR": "❌ Hayır",
    "GEC": "⏭️ Geç",
}

# ============================================
# ⚠️ HATA MESAJLARI
# ============================================

ERRORS = {
    "GENEL": "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
    "YETKISIZ": "❌ Bu işlem için yetkiniz yok.",
    "GRUP_DEGIL": "❌ Bu komut sadece gruplarda çalışır.",
    "OZEL_DEGIL": "❌ Bu komut sadece özelden çalışır.",
    "GECERSIZ_SAYI": "❌ Geçersiz sayı. Lütfen bir sayı girin.",
}

# ============================================
# ✅ BAŞARI MESAJLARI
# ============================================

SUCCESS = {
    "KAYDEDILDI": "✅ Başarıyla kaydedildi!",
    "GUNCELLENDI": "✅ Başarıyla güncellendi!",
    "SILINDI": "✅ Başarıyla silindi!",
}


def format_winner_list(winners: list) -> str:
    """Kazanan listesini formatla (tıklanabilir mention)"""
    if not winners:
        return "Kazanan yok"

    result = []
    for i, w in enumerate(winners, 1):
        telegram_id = w.get("telegram_id")
        first_name = w.get("first_name", "Kullanıcı")
        username = w.get("username")

        # Her zaman tıklanabilir mention kullan
        if telegram_id:
            # Username varsa parantez içinde göster
            if username:
                name = f'<a href="tg://user?id={telegram_id}">{first_name}</a> (@{username})'
            else:
                name = f'<a href="tg://user?id={telegram_id}">{first_name}</a>'
        else:
            # telegram_id yoksa (olmaması lazım ama fallback)
            if username:
                name = f"@{username}"
            else:
                name = first_name

        result.append(f"{i}. {name}")

    return "\n".join(result)


def format_user_mention(user_id: int, first_name: str) -> str:
    """Kullanıcı mention oluştur"""
    return f'<a href="tg://user?id={user_id}">{first_name}</a>'


def format_roll_list(users: list, step_number: int = None) -> str:
    """Roll kullanıcı listesini formatla"""
    if not users:
        return "📭 Kullanıcı yok."

    # Mesaj sayısına göre sırala
    sorted_users = sorted(users, key=lambda x: x.get("message_count", 0), reverse=True)

    header = f"📍 Adım {step_number}\n" if step_number else ""

    lines = []
    for u in sorted_users:
        name = u.get("name", "Kullanıcı")
        count = u.get("message_count", 0)
        lines.append(f"✅ {name} • {count} ✉️")

    return header + "\n".join(lines)


def get_period_text(period: str) -> str:
    """Periyod metnini döndür"""
    periods = {
        "daily": "Bugün",
        "weekly": "Bu hafta",
        "monthly": "Bu ay",
        "all_time": "Toplam",
        "post_randy": "Randy sonrası"
    }
    return periods.get(period, period)


def get_media_type_text(media_type: str) -> str:
    """Medya tipi metnini döndür"""
    types = {
        "none": "Yok",
        "photo": "Fotoğraf",
        "video": "Video",
        "animation": "GIF"
    }
    return types.get(media_type, "Yok")

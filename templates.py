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
        "Bot, gönderdiğiniz premium emojiyi otomatik algılar.\n\n"
        "<b>🤖 Otomatik Etiket:</b>\n"
        "Aşağıdaki butonlardan otomatik etiket ayarlarını yapabilirsiniz."
    ),

    # Otomatik Etiket Menüsü
    "AUTO_TAG_MENU": (
        "🤖 <b>Otomatik Etiket Ayarları</b>\n\n"
        "Bot, belirlediğiniz aralıklarla otomatik olarak "
        "rastgele 1 kullanıcıyı etiketler.\n\n"
        "<b>Mevcut Ayarlar:</b>\n"
        "• Durum: {status}\n"
        "• Aralık: {interval} dakika\n"
        "• Tip: {tag_type}\n\n"
        "<b>📌 Not:</b>\n"
        "• Her seferinde 1 rastgele kullanıcı etiketlenir\n"
        "• Etiketleme aralığı ±2 dakika rastgele değişir\n"
        "• Manuel etiketleme sırasında otomatik etiket duraklar"
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

    # Çekiliş Menüsü
    "CEKILIS_MENU": (
        "🎁 <b>Çekiliş Yönetimi</b>\n\n"
        "Rastgele zamanlı otomatik çekiliş sistemi.\n\n"
        "<b>📝 Nasıl Çalışır:</b>\n"
        "1️⃣ Çekilişi başlat (süre + kazanan sayısı)\n"
        "2️⃣ Sistem rastgele zamanlar belirler\n"
        "3️⃣ O zamanlarda mesaj yazan İLK kişi kazanır\n"
        "4️⃣ Kazananın mesajına reply atılır\n\n"
        "<b>📢 Komutlar (Grupta):</b>\n"
        "• <code>/cekilis [ödül]</code> - Hızlı başlat\n"
        "• <code>/cekilis iptal</code> - İptal et\n\n"
        "<i>🤖 Botlar çekilişe katılamaz.</i>"
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
        "👤 <b>{name}</b> {username_line}\n\n"
        "💬 <b>Mesajlar</b>\n"
        "    Bugün  ➜  <b>{daily}</b>\n"
        "    Hafta  ➜  <b>{weekly}</b>\n"
        "    Ay  ➜  <b>{monthly}</b>\n"
        "    Toplam  ➜  <b>{total}</b>\n\n"
        "📊 <b>Sıralama</b>\n"
        "    Haftalık  ➜  <b>{weekly_rank}</b>\n"
        "    Ort/Gün  ➜  <b>~{daily_avg}</b>\n\n"
        "🎲 <b>Randy</b>\n"
        "    Katılım  ➜  <b>{randy_participated}</b>\n"
        "    Kazanma  ➜  <b>{randy_won}</b>\n"
        "{win_rate_line}"
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

    # Otomatik Etiket
    "AUTO_TAG_ON": "🟢 Otomatik Etiket Aç",
    "AUTO_TAG_OFF": "🔴 Otomatik Etiket Kapat",
    "AUTO_TAG_INTERVAL": "⏱️ Aralık Ayarla",
    "AUTO_TAG_30": "30 Dakika",
    "AUTO_TAG_60": "1 Saat",
    "AUTO_TAG_120": "2 Saat",
    "AUTO_TAG_180": "3 Saat",

    # Çekiliş
    "CEKILIS_YONETIMI": "🎁 Çekiliş",
    "CEKILIS_AYARLARI": "⚙️ Çekiliş Ayarları",
    "CEKILIS_BASLAT": "🎁 Yeni Çekiliş",
    "AKTIF_CEKILIS": "🎯 Aktif Çekiliş",
    "GECMIS_CEKILISLER": "📜 Geçmiş Çekilişler",
    "EN_COK_KAZANANLAR": "🏆 En Çok Kazananlar",
    "CEKILIS_IPTAL": "❌ Çekilişi İptal Et",
    "SURE_AYARLA": "⏱️ Süre",
    "KAZANAN_LIMIT": "🔢 Kişi Başı Limit",
    "DUYURU_SABITLE": "📌 Duyuru Sabitle",
    "KAZANAN_SABITLE": "📌 Kazanan Sabitle",
    "YONETIM_BILDIR": "📢 Yönetime Bildir",
    "YONETIMDE_SABITLE": "📌 Yönetimde Sabitle",
    "YONETIM_GRUBU": "👥 Yönetim Grubu",

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


# ============================================
# 🎁 ÇEKİLİŞ MESAJLARI
# ============================================

GIVEAWAY = {
    "MENU": (
        "🎁 <b>Çekiliş Yönetimi</b>\n\n"
        "Rastgele zamanlı otomatik çekiliş sistemi.\n\n"
        "<b>Nasıl Çalışır:</b>\n"
        "1️⃣ Çekilişi başlat (süre + kazanan sayısı)\n"
        "2️⃣ Sistem rastgele zamanlar belirler\n"
        "3️⃣ O zamanlarda mesaj yazan İLK kişi kazanır\n"
        "4️⃣ Kazananın mesajına reply atılır\n\n"
        "<i>Botlar çekilişe katılamaz.</i>"
    ),

    "SETTINGS_MENU": (
        "⚙️ <b>Çekiliş Ayarları</b>\n\n"
        "Varsayılan çekiliş ayarlarını yapılandırın.\n\n"
        "<b>Mevcut Ayarlar:</b>\n"
        "• Süre: {duration} saat\n"
        "• Kazanan: {winners} kişi\n"
        "• Kişi başı limit: {max_wins}\n"
        "• Duyuru sabitle: {pin_ann}\n"
        "• Kazanan mesajı sabitle: {pin_win}\n"
        "• Yönetim bildirimi: {notify_admin}\n"
        "• Yönetimde sabitle: {pin_admin}"
    ),

    "ACTIVE_GIVEAWAY": (
        "🎁 <b>Aktif Çekiliş</b>\n\n"
        "🎯 <b>Ödül:</b> {prize}\n"
        "⏱️ <b>Süre:</b> {duration} saat\n"
        "🏆 <b>Kazanan Sayısı:</b> {winner_count}\n"
        "📅 <b>Başlangıç:</b> {start_time}\n"
        "⏰ <b>Bitiş:</b> {end_time}\n\n"
        "<b>Kazanma Zamanları:</b>\n{win_times}\n\n"
        "<i>Bu zamanlar gizlidir, sadece adminler görebilir.</i>"
    ),

    "NO_ACTIVE": "❌ Şu anda aktif çekiliş yok.",

    "ALREADY_ACTIVE": "⚠️ Bu grupta zaten aktif bir çekiliş var.",

    "ANNOUNCEMENT": (
        "🎁 <b>ÇEKİLİŞ BAŞLADI!</b>\n\n"
        "🎯 <b>Ödül:</b> {prize}\n"
        "⏱️ <b>Süre:</b> {duration} saat\n"
        "🏆 <b>Kazanan:</b> {winner_count} kişi\n\n"
        "📝 <b>Gruba Mesaj Yazanlardan Rastgele Kişiler Seçilir</b>\n"
    ),

    "WINNER_MESSAGE": (
        "🎉 <b>TEBRİKLER!</b>\n\n"
        "Çekilişi kazandınız!\n\n"
        "🎯 <b>Ödül:</b> {prize}\n"
        "🏆 <b>Slot:</b> {slot}/{total}\n"
        "⏰ <b>Zaman:</b> {time}\n\n"
        "@msharleydestek Size Ulaşacaktır."
    ),

    "ADMIN_NOTIFICATION": (
        "🎁 <b>ÇEKİLİŞ KAZANANI</b>\n\n"
        "👤 Kazanan: {winner_mention}\n"
        "🎯 Ödül: {prize}\n"
        "🏆 Slot: {slot}/{total}\n"
        "⏰ Zaman: {time}\n"
        "💬 Grup: {group_name}"
    ),

    "ENDED": (
        "🎊 <b>ÇEKİLİŞ SONA ERDİ!</b>\n\n"
        "🎯 <b>Ödül:</b> {prize}\n\n"
        "<b>Kazananlar:</b>\n{winner_list}"
    ),

    "PAST_GIVEAWAYS": (
        "📜 <b>Geçmiş Çekilişler</b>\n\n"
        "{giveaway_list}\n\n"
        "<i>Son {count} çekiliş gösteriliyor.</i>"
    ),

    "NO_PAST": "📭 Henüz geçmiş çekiliş yok.",

    "TOP_WINNERS": (
        "🏆 <b>En Çok Kazananlar</b>\n\n"
        "{winner_list}"
    ),

    "CREATE_PROMPT_PRIZE": "🎯 <b>Ödül Metni</b>\n\nÇekiliş ödülünü yazın:\n\n<i>Örnek: 100 TL </i>",

    "CREATE_PROMPT_DURATION": "⏱️ <b>Süre</b>\n\nÇekiliş kaç saat sürecek?\n\n<i>Örnek: 2</i>",

    "CREATE_PROMPT_WINNERS": "🏆 <b>Kazanan Sayısı</b>\n\nKaç kişi kazanacak?\n\n<i>Örnek: 3</i>",

    "CANCELLED": "❌ Çekiliş iptal edildi.",

    "WIN_LIMIT_REACHED": "⚠️ Bu çekilişte kazanma limitinize ulaştınız.",
}


# ============================================
# 🏆 HAFTALIK AKTİVİTE ÖDÜL MESAJLARI
# ============================================

WEEKLY_REWARDS = {
    "MENU": (
        "🏆 <b>Haftalık Aktivite Ödülleri</b>\n\n"
        "Her hafta en aktif üyelere ödül verilir.\n"
        "Adminler bu listeye dahil değildir.\n\n"
        "<b>Mevcut Ayarlar:</b>\n"
        "• Durum: {status}\n"
        "• Top sayısı: {top_count} kişi\n"
        "• Otomatik paylaşım: {auto_post}\n"
        "• Otomatik sabitle: {auto_pin}\n"
        "• Paylaşım saati: Pazar {post_time}\n\n"
        "<b>Ödüller:</b>\n{rewards_list}"
    ),

    "SET_REWARD_PROMPT": (
        "🎁 <b>{rank}. Sıra Ödülü</b>\n\n"
        "Bu sıra için ödül metnini yazın.\n\n"
        "<i>Örnek: 50 TL Hediye Çeki</i>"
    ),

    "REWARD_SAVED": "✅ {rank}. sıra ödülü kaydedildi: <b>{reward}</b>",

    "LEADERBOARD": (
        "🏆 <b>HAFTALIK AKTİVİTE LİDERLERİ</b>\n\n"
        "📅 Hafta: {week_info}\n\n"
        "{leaderboard}\n\n"
        "🎯 <i>Haftaya da aktif ol, ödülleri kap!</i>"
    ),

    "LEADERBOARD_ROW": "{medal} {mention} - {count}",
    "LEADERBOARD_ROW_REWARD": "{medal} {mention} - {count} - {reward}",

    "NO_DATA": "📭 Bu hafta henüz yeterli veri yok.",

    "ALREADY_POSTED": "⚠️ Bu hafta zaten paylaşım yapıldı.",

    "REWARD_NOT_SET": "<i>Ödül tanımlanmamış</i>",

    "AUTO_POST_MESSAGE": (
        "🏆 <b>HAFTANIN EN AKTİFLERİ!</b>\n\n"
        "Bu haftanın en aktif {count} üyesini kutluyoruz!\n\n"
        "{leaderboard}\n\n"
        "🎉 <b>Tebrikler!</b>\n"
        "Ödülleriniz için yöneticilerimizle iletişime geçin.\n\n"
        "💪 <i>Yeni hafta, yeni şans! Aktif ol, kazan!</i>"
    ),
}


def format_weekly_leaderboard(leaderboard: list, show_rewards: bool = True) -> str:
    """Haftalık liderlik tablosunu formatla"""
    if not leaderboard:
        return WEEKLY_REWARDS["NO_DATA"]

    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    lines = []

    for user in leaderboard:
        rank = user.get('rank', 1)
        medal = medals[rank - 1] if rank <= len(medals) else f"{rank}."

        # Mention oluştur - her zaman tıklanabilir link kullan
        telegram_id = user.get('telegram_id')
        first_name = user.get('first_name', 'Kullanıcı')
        username = user.get('username')

        # Görüntülenecek ismi belirle - username öncelikli
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = "Kullanıcı"

        # Her zaman tıklanabilir mention kullan (telegram_id varsa)
        if telegram_id:
            mention = f'<a href="tg://user?id={telegram_id}">{display_name}</a>'
        else:
            mention = display_name

        count = user.get('weekly_count', 0)
        reward = user.get('reward')

        if show_rewards and reward:
            line = WEEKLY_REWARDS["LEADERBOARD_ROW_REWARD"].format(
                medal=medal, mention=mention, count=count, reward=reward
            )
        else:
            line = WEEKLY_REWARDS["LEADERBOARD_ROW"].format(
                medal=medal, mention=mention, count=count
            )

        lines.append(line)

    return "\n".join(lines)


def format_rewards_list(rewards: list, top_count: int = 5) -> str:
    """Ödül listesini formatla"""
    if not rewards:
        return "Henüz ödül tanımlanmamış."

    rewards_dict = {r['rank']: r['reward_text'] for r in rewards}
    lines = []

    for i in range(1, top_count + 1):
        reward = rewards_dict.get(i, "—")
        lines.append(f"  {i}. {reward}")

    return "\n".join(lines)


def format_winner_list(winners: list) -> str:
    """Kazanan listesini formatla (tıklanabilir mention)"""
    if not winners:
        return "Kazanan yok"

    result = []
    for i, w in enumerate(winners, 1):
        telegram_id = w.get("telegram_id")
        first_name = w.get("first_name")
        username = w.get("username")

        # Görüntülenecek ismi belirle - username öncelikli
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = "Kullanıcı"

        # Her zaman tıklanabilir mention kullan
        if telegram_id:
            name = f'<a href="tg://user?id={telegram_id}">{display_name}</a>'
        else:
            # telegram_id yoksa (olmaması lazım ama fallback)
            name = display_name

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


def format_giveaway_win_times(win_times: list, show_winners: bool = True) -> str:
    """Çekiliş kazanma zamanlarını formatla"""
    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    lines = []
    for wt in win_times:
        win_time = wt.get('win_time')
        slot_num = wt.get('slot_number', 0)
        is_won = wt.get('is_won', False)

        if win_time:
            if win_time.tzinfo is None:
                win_time = win_time.replace(tzinfo=timezone.utc)
            local_time = win_time.astimezone(TR_TZ)
            time_str = local_time.strftime("%H:%M")
        else:
            time_str = "??:??"

        if is_won and show_winners:
            winner_name = wt.get('winner_first_name', 'Kazanan')
            winner_username = wt.get('winner_username')
            winner_id = wt.get('winner_id')

            # Görüntülenecek ismi belirle - username öncelikli
            if winner_username:
                display_name = f"@{winner_username}"
            elif winner_name and winner_name != 'Kazanan':
                display_name = winner_name
            else:
                display_name = "Kazanan"

            # Her zaman tıklanabilir mention kullan (winner_id varsa)
            if winner_id:
                winner_text = f'<a href="tg://user?id={winner_id}">{display_name}</a>'
            else:
                winner_text = display_name
            lines.append(f"✅ Slot {slot_num}: {time_str} - {winner_text}")
        elif is_won:
            lines.append(f"✅ Slot {slot_num}: {time_str} - Kazanıldı")
        else:
            lines.append(f"⏳ Slot {slot_num}: {time_str} - Bekliyor")

    return "\n".join(lines) if lines else "Zaman belirlenmedi"


def format_giveaway_list(giveaways: list) -> str:
    """Geçmiş çekilişleri formatla"""
    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    TR_TZ = ZoneInfo("Europe/Istanbul")

    lines = []
    for g in giveaways:
        giveaway_id = g.get('id')
        prize = g.get('prize_text', 'Ödül')
        status = g.get('status', 'ended')
        ended_at = g.get('ended_at')

        status_emoji = "🎊" if status == 'ended' else "❌"

        if ended_at:
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=timezone.utc)
            local_time = ended_at.astimezone(TR_TZ)
            date_str = local_time.strftime("%d.%m.%Y %H:%M")
        else:
            date_str = "-"

        # Ödül metnini kısalt
        if len(prize) > 30:
            prize = prize[:27] + "..."

        lines.append(f"{status_emoji} #{giveaway_id} | {prize} | {date_str}")

    return "\n".join(lines) if lines else "Çekiliş yok"


def format_top_winners(winners: list) -> str:
    """En çok kazananları formatla"""
    lines = []
    for i, w in enumerate(winners, 1):
        user_id = w.get('user_id')
        win_count = w.get('win_count', 0)
        first_name = w.get('first_name', 'Kullanıcı')
        username = w.get('username')

        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

        # Görüntülenecek ismi belirle - username öncelikli
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = "Kullanıcı"

        # Her zaman tıklanabilir mention kullan (user_id varsa)
        if user_id:
            name = f'<a href="tg://user?id={user_id}">{display_name}</a>'
        else:
            name = display_name

        lines.append(f"{medal} {name} - {win_count} kazanma")

    return "\n".join(lines) if lines else "Henüz kazanan yok"

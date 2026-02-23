# Randy & Roll Bot - TODO List
https://github.com/Semhkaramn/tamsite.git bana bu projedeki randy sistemini ve roll sistemini yapan bir py dosyası yapmanı istiyorum komutlar özelden veya gruptan yapılabiilir randy ayarları /randy yazınca başlayacak /number 4 kazanan seçecek /mesaj günlük 5 haftalık 100 gibi mesaj şartı olacak bot mesajları sayacak .me .günlük . haftalık vs olacak ama puan sistmei olmayacak randy mesajını da şöyle ayarlayacağız özelden ayarlanacak herşey geri kalan kanal takip ayarları vs herşey butonlu arayüz sisteminden ayarlaranacak geri tuşları randy medya seçimi metin seçimi $kazanan yazısını metin kısmında nereye koyarsam orada randy açılınca katılımca sayısı gözükmeli gruptaki mesajları kaydedecek özelden ayar yaparken o belirlediğimiz grubun admini mi otomatik bakacak ayarlamaları komutları hepsini adminler yapabili sadece mesaj sayarken kanal mesajları bot mesajları telegram mesajları gibi şeyleri saymamalı zaten tüm dediklerimi anladın mı onlarla ilgili tüm kodları oku detaylı bir todos oluştur ve botumu parçalı halde yap

## Proje Özeti
Telegram botu - Heroku'da çalışacak, Neon.tech PostgreSQL kullanacak.
Puan sistemi YOK - sadece mesaj sayma ve çekiliş sistemi. randy mesajı formatı hem görselli hemm mesajlı olabilir ve kanal kontrolü eklerken kullanıcı adıyla ekleyebilmeliyiz

---

## 1. PROJE YAPISI
- [x] Proje klasörünü oluştur
- [x] Modüler dosya yapısı kur:
  - `bot.py` - Ana bot başlatıcı ✅ (oluşturulacak)
  - `config.py` - Ayarlar ve environment variables ✅
  - `database.py` - PostgreSQL bağlantısı ve modeller ✅
  - `handlers/` - Komut ve callback handler'ları
    - `__init__.py` ✅
    - `commands.py` - Grup/özel komutlar ✅ (oluşturulacak)
    - `callbacks.py` - Buton callback'leri ✅
    - `messages.py` - Mesaj işleme ✅ (oluşturulacak)
    - `admin_settings.py` - Özelden admin ayarları ✅ (oluşturulacak)
  - `services/` - İş mantığı
    - `__init__.py` ✅
    - `randy_service.py` - Randy (çekiliş) işlemleri ✅
    - `roll_service.py` - Roll sistemi işlemleri ✅
    - `message_service.py` - Mesaj sayma işlemleri ✅
  - `utils/` - Yardımcı fonksiyonlar
    - `__init__.py` ✅
    - `telegram_utils.py` - Telegram API yardımcıları ✅ (oluşturulacak)
    - `admin_check.py` - Admin kontrolü ✅
    - `formatters.py` - Mesaj formatlama ✅ (oluşturulacak)
  - `templates.py` - Mesaj taslakları ✅
  - `requirements.txt` - Bağımlılıklar ✅ (oluşturulacak)
  - `Procfile` - Heroku için ✅ (oluşturulacak)
  - `runtime.txt` - Python versiyonu ✅ (oluşturulacak)

---

## 2. VERİTABANI YAPISI (Neon.tech PostgreSQL)

### Tablolar:
- [x] `telegram_groups` - Bot eklenen gruplar
- [x] `telegram_users` - Kullanıcı mesaj istatistikleri
- [x] `group_admins` - Grup adminleri cache
- [x] `randy` - Çekiliş kayıtları
- [x] `randy_participants` - Çekilişe katılanlar
- [x] `randy_winners` - Kazananlar
- [x] `roll_sessions` - Roll oturumları
- [x] `roll_steps` - Roll adımları
- [x] `roll_step_users` - Adımdaki kullanıcılar
- [x] `randy_drafts` - Randy taslakları

---

## 3. RANDY SİSTEMİ

### Özellikler:
- [x] `/randy` - Admin özelden randy ayar menüsünü aç
- [x] `/number X` - Kazanan sayısını ayarla
- [x] Mesaj şartları (günlük, haftalık, aylık, toplam, randy sonrası, şartsız)
- [x] Kanal takip zorunluluğu
- [x] Randy mesaj özelleştirme ($kazanan placeholder)
- [x] Medya seçimi (foto/video/gif/sadece metin)
- [x] Katılım sayısı gösterimi
- [x] Butonlu arayüz (özelden ayarlama)
- [x] Geri tuşları
- [x] Admin kontrolü (otomatik)
- [ ] Randy başlat/bitir (komut handler'ları eklenmeli)

### Özelden Ayar Menüsü:
- [x] "Randy Oluştur" butonu
- [x] Grup seçimi (admin olduğu gruplar)
- [x] Mesaj düzenleme
- [x] Medya ekleme
- [x] Şart seçimi
- [ ] Kanal ekleme (kullanıcı adıyla)
- [x] Kazanan sayısı
- [x] Önizleme
- [x] Kaydet

---

## 4. ROLL SİSTEMİ

### Komutlar (Grup - Sadece Admin):
- [x] `roll X` - X dakika süreli roll başlat (service hazır)
- [x] `roll adım` - Adımı kaydet ve duraklat
- [x] `roll devam` - Yeni adım ile devam
- [x] `roll mola` - Mola ver
- [x] `roll kilit` - Yeni kullanıcı girişini kapat
- [x] `roll aç` - Kilidi aç
- [x] `roll bitir` - Roll'u sonlandır
- [x] `liste` - Mevcut durumu göster
- [ ] Handler'ları oluştur

### Özellikler:
- [x] Süre bazlı inaktif kullanıcı silme
- [x] Adım bazlı kullanıcı listesi
- [x] Mesaj sayısına göre sıralama
- [x] Kilit + mola kombinasyonu
- [x] Restart'a dayanıklı (DB tabanlı)

---

## 5. MESAJ SAYMA SİSTEMİ

### Komutlar:
- [x] `.me` / `!me` / `/me` - Kendi istatistiklerini gör (service hazır)
- [x] `.günlük` / `.daily` - Günlük mesaj sayısı
- [x] `.haftalık` / `.weekly` - Haftalık mesaj sayısı
- [x] `.aylık` / `.monthly` - Aylık mesaj sayısı
- [ ] Handler'ları oluştur

### Özellikler:
- [x] Bot mesajlarını sayma
- [x] Kanal mesajlarını sayma
- [x] Telegram servis hesabı (777000) sayma
- [x] Anonim admin mesajlarını sayma (1087968824)
- [x] Günlük/haftalık/aylık sıfırlama

---

## 6. ADMIN KONTROLÜ

### Özellikler:
- [x] Telegram API ile admin kontrolü
- [x] Admin cache (5 dakika)
- [x] Özelden ayar yapılırken grup admin kontrolü
- [x] Anonim admin desteği (sender_chat)

---

## 7. TELEGRAM API

### Fonksiyonlar:
- [ ] sendMessage (HTML parse mode)
- [ ] editMessageText
- [ ] deleteMessage
- [ ] answerCallbackQuery
- [ ] pinChatMessage
- [ ] getChatMember (admin kontrolü)
- [ ] getChatAdministrators
- [ ] getChatInfo
- [ ] sendPhoto / sendVideo / sendAnimation

---

## 8. HEROKU DEPLOYMENT

### Dosyalar:
- [ ] `Procfile` - worker: python bot.py
- [ ] `runtime.txt` - python-3.11.x
- [ ] `requirements.txt` - bağımlılıklar

### Environment Variables:
- [ ] BOT_TOKEN - Telegram bot token
- [ ] DATABASE_URL - Neon.tech connection string
- [ ] WEBHOOK_URL (opsiyonel - polling kullanılacak)

---

## 9. MESAJ TASLKLARI (templates.py)

### Kategoriler:
- [ ] GENEL - Hoş geldin, hata mesajları
- [ ] ISTATISTIK - .me komutu mesajları
- [ ] ROLL - Roll sistemi mesajları
- [ ] RANDY - Randy/çekiliş mesajları
- [ ] ADMIN - Admin menü mesajları

---

## 10. CALLBACK DATA YAPISI

### Format:
- `randy_create` - Randy oluşturma başlat
- `randy_group_{id}` - Grup seç
- `randy_req_{type}` - Şart tipi seç
- `randy_msg_count_{count}` - Mesaj sayısı ayarla
- `randy_media_{type}` - Medya tipi seç
- `randy_preview` - Önizleme
- `randy_publish` - Yayınla
- `randy_join_{id}` - Randy'ye katıl
- `randy_back` - Geri dön
- `admin_settings` - Ayarlar menüsü

---

## İlerleme Durumu

### Tamamlanan:
- [x] Proje analizi
- [x] Kod incelemesi
- [x] TODO listesi oluşturma
- [x] Veritabanı şeması
- [x] Servisler (randy, roll, message)
- [x] Admin kontrolü
- [x] Callback handler'ları
- [x] Mesaj taslakları

### Devam Eden:
- [ ] bot.py - Ana bot başlatıcı
- [ ] handlers/commands.py - Komut handler'ları
- [ ] handlers/messages.py - Mesaj handler'ları
- [ ] Deployment dosyaları

### Bekleyen:
- [ ] Test
- [ ] Deployment

Şimdi mevcut bot projesinin tüm dosyalarını gördüm ve referans tamsite projesindeki Randy ve Roll sistemini inceledim. Todo'lara göre eksik olanları tamamlamamız gerekiyor:

Tamamlanan:

Database.py ✅
Config.py ✅
Services (randy, roll, message) ✅
Admin kontrolü ✅
Callback handler'ları ✅
Mesaj taslakları ✅
Commands.py ✅
Messages.py ✅
Devam Eden / Eksik olan:

end_randy_with_count fonksiyonu (randy_service.py'de yok) - /number komutu bu fonksiyonu kullanıyor
format_winner_list fonksiyonu (templates.py'de kontrol edilmeli)
templates.py dosyasında RANDY template'leri
requirements.txt - bağımlılıklar
Procfile - Heroku için
runtime.txt - Python versiyonu
Kanal ekleme (kullanıcı adıyla) - callback'lerde eksik
Şimdi önce mevcut templates.py dosyasını kontrol edeyim:

## 🐛 Tespit Edilen Mantıksal Hatalar

1. [x] `get_status_list` fonksiyonu `return_raw=True` parametresi ile çağrılıyor ama fonksiyon tanımında bu parametre yok
2. [x] TR saat dilimi offset'i için daha güvenilir bir yöntem kullanılmalı (pytz veya zoneinfo)
3. [x] `/randy` komutu grupta silinmiyor - silindikten sonra Randy başlamalı
4. [x] Taslaklar `creator_id` bazlı kaydediliyor - grup bazlı olmalı ki tüm adminler görebilsin
5. [x] Reply ile Randy bitirme özelliği yok

## ✨ İstenen Yeni Özellikler

1. [x] Gruplarda /randy yazınca komut silinip Randy başlasın
2. [x] Kanallarda admin ayarı için ACTIVITY_GROUP_ID kullanımı düzeltilmeli
3. [x] Reply ile Randy bitirme (admin reply yaparsa bitirebilmeli)
4. [x] Tüm adminler aynı Randy taslağını görmeli (grup bazlı taslak)
5. [x] Randy mesajı hem görsel hem yazılı olabilmeli (zaten var - media_type)
6. [x] Özelden /start yazınca adminse tüm menü gözükmeli
7. [x] TR saatine göre sıfırlama düzeltmesi

## 📝 Yapılan Değişiklikler

- [ ] roll_service.py - get_status_list return_raw parametresi eklendi
- [ ] message_service.py - TR saat dilimi düzeltmesi
- [ ] commands.py - /randy komutu silme özelliği
- [ ] commands.py - Reply ile bitirme özelliği
- [ ] randy_service.py - Grup bazlı taslak sistemi
- [ ] callbacks.py - Admin senkronizasyonu için güncelleme

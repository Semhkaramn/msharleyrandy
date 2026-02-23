# Randy & Roll Bot - TODO List
https://github.com/Semhkaramn/tamsite.git bana bu projedeki randy sistemini ve roll sistemini yapan bir py dosyası yapmanı istiyorum komutlar özelden veya gruptan yapılabiilir randy ayarları /randy yazınca başlayacak /number 4 kazanan seçecek /mesaj günlük 5 haftalık 100 gibi mesaj şartı olacak bot mesajları sayacak .me .günlük . haftalık vs olacak ama puan sistmei olmayacak randy mesajını da şöyle ayarlayacağız özelden ayarlanacak herşey geri kalan kanal takip ayarları vs herşey butonlu arayüz sisteminden ayarlaranacak geri tuşları randy medya seçimi metin seçimi $kazanan yazısını metin kısmında nereye koyarsam orada randy açılınca katılımca sayısı gözükmeli gruptaki mesajları kaydedecek özelden ayar yaparken o belirlediğimiz grubun admini mi otomatik bakacak ayarlamaları komutları hepsini adminler yapabili sadece mesaj sayarken kanal mesajları bot mesajları telegram mesajları gibi şeyleri saymamalı zaten tüm dediklerimi anladın mı onlarla ilgili tüm kodları oku detaylı bir todos oluştur ve botumu parçalı halde yap

## Proje Özeti
Telegram botu - Heroku'da çalışacak, Neon.tech PostgreSQL kullanacak.
Puan sistemi YOK - sadece mesaj sayma ve çekiliş sistemi. randy mesajı formatı hem görselli hemm mesajlı olabilir ve kanal kontrolü eklerken kullanıcı adıyla ekleyebilmeliyiz 

---

## 1. PROJE YAPISI
- [x] Proje klasörünü oluştur
- [ ] Modüler dosya yapısı kur:
  - `bot.py` - Ana bot başlatıcı
  - `config.py` - Ayarlar ve environment variables
  - `database.py` - PostgreSQL bağlantısı ve modeller
  - `handlers/` - Komut ve callback handler'ları
    - `__init__.py`
    - `commands.py` - Grup/özel komutlar
    - `callbacks.py` - Buton callback'leri
    - `messages.py` - Mesaj işleme
    - `admin_settings.py` - Özelden admin ayarları
  - `services/` - İş mantığı
    - `__init__.py`
    - `randy_service.py` - Randy (çekiliş) işlemleri
    - `roll_service.py` - Roll sistemi işlemleri
    - `message_service.py` - Mesaj sayma işlemleri
  - `utils/` - Yardımcı fonksiyonlar
    - `__init__.py`
    - `telegram_utils.py` - Telegram API yardımcıları
    - `admin_check.py` - Admin kontrolü
    - `formatters.py` - Mesaj formatlama
  - `templates.py` - Mesaj taslakları
  - `requirements.txt` - Bağımlılıklar
  - `Procfile` - Heroku için
  - `runtime.txt` - Python versiyonu

---

## 2. VERİTABANI YAPISI (Neon.tech PostgreSQL)

### Tablolar:
- [ ] `telegram_groups` - Bot eklenen gruplar
  - id, group_id, title, is_active, created_at

- [ ] `telegram_users` - Kullanıcı mesaj istatistikleri
  - id, telegram_id, username, first_name, last_name
  - message_count, daily_count, weekly_count, monthly_count
  - last_message_at, last_daily_reset, last_weekly_reset, last_monthly_reset
  - created_at, updated_at

- [ ] `group_admins` - Grup adminleri cache
  - id, group_id, user_id, is_admin, updated_at

- [ ] `randy` - Çekiliş kayıtları
  - id, group_id, title, message, media_type, media_file_id
  - requirement_type (none/daily/weekly/monthly/all_time/post_randy)
  - required_message_count, winner_count
  - channel_ids (zorunlu kanal üyelikleri)
  - status (draft/active/ended), message_id
  - pin_message, started_at, ended_at, created_at

- [ ] `randy_participants` - Çekilişe katılanlar
  - id, randy_id, telegram_id, username, first_name
  - post_randy_message_count, joined_at

- [ ] `randy_winners` - Kazananlar
  - id, randy_id, telegram_id, username, first_name, won_at

- [ ] `roll_sessions` - Roll oturumları
  - id, group_id, status, active_duration, current_step
  - previous_status, created_at, updated_at

- [ ] `roll_steps` - Roll adımları
  - id, session_id, step_number, is_active, created_at

- [ ] `roll_step_users` - Adımdaki kullanıcılar
  - id, step_id, telegram_id, name, message_count, last_active

---

## 3. RANDY SİSTEMİ

### Özellikler:
- [ ] `/randy` - Admin özelden randy ayar menüsünü aç
- [ ] `/number X` - Kazanan sayısını ayarla
- [ ] Mesaj şartları:
  - Günlük X mesaj
  - Haftalık X mesaj
  - Aylık X mesaj
  - Toplam X mesaj
  - Randy sonrası X mesaj
  - Şartsız
- [ ] Kanal takip zorunluluğu
- [ ] Randy mesaj özelleştirme:
  - $kazanan placeholder
  - Medya seçimi (foto/video/gif/sadece metin)
- [ ] Katılım sayısı gösterimi
- [ ] Butonlu arayüz (özelden ayarlama)
- [ ] Geri tuşları
- [ ] Admin kontrolü (otomatik)
- [ ] Randy başlat/bitir

### Özelden Ayar Menüsü:
- [ ] "Randy Oluştur" butonu
- [ ] Grup seçimi (admin olduğu gruplar)
- [ ] Mesaj düzenleme
- [ ] Medya ekleme
- [ ] Şart seçimi
- [ ] Kanal ekleme
- [ ] Kazanan sayısı
- [ ] Önizleme
- [ ] Yayınla

---

## 4. ROLL SİSTEMİ

### Komutlar (Grup - Sadece Admin):
- [ ] `roll X` - X dakika süreli roll başlat
- [ ] `roll adım` - Adımı kaydet ve duraklat
- [ ] `roll devam` - Yeni adım ile devam
- [ ] `roll mola` - Mola ver
- [ ] `roll kilit` - Yeni kullanıcı girişini kapat
- [ ] `roll aç` - Kilidi aç
- [ ] `roll bitir` - Roll'u sonlandır
- [ ] `liste` - Mevcut durumu göster

### Özellikler:
- [ ] Süre bazlı inaktif kullanıcı silme
- [ ] Adım bazlı kullanıcı listesi
- [ ] Mesaj sayısına göre sıralama
- [ ] Kilit + mola kombinasyonu
- [ ] Restart'a dayanıklı (DB tabanlı)

---

## 5. MESAJ SAYMA SİSTEMİ

### Komutlar:
- [ ] `.me` / `!me` / `/me` - Kendi istatistiklerini gör
- [ ] `.günlük` / `.daily` - Günlük mesaj sayısı
- [ ] `.haftalık` / `.weekly` - Haftalık mesaj sayısı
- [ ] `.aylık` / `.monthly` - Aylık mesaj sayısı

### Özellikler:
- [ ] Bot mesajlarını sayma
- [ ] Kanal mesajlarını sayma
- [ ] Telegram servis hesabı (777000) sayma
- [ ] Anonim admin mesajlarını sayma (1087968824)
- [ ] Günlük/haftalık/aylık sıfırlama

---

## 6. ADMIN KONTROLÜ

### Özellikler:
- [ ] Telegram API ile admin kontrolü
- [ ] Admin cache (5 dakika)
- [ ] Özelden ayar yapılırken grup admin kontrolü
- [ ] Anonim admin desteği (sender_chat)

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

### Devam Eden:
- [ ] Modüler dosya yapısı oluşturma

### Bekleyen:
- [ ] Veritabanı şeması
- [ ] Handler'lar
- [ ] Servisler
- [ ] Test

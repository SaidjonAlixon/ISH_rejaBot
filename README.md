# 🤖 IshBot - Vazifa Boshqarish Tizimi

O'zbek tilida ishlaydigan Telegram bot orqali tashkilot ichida vazifalarni taqsimlash va bajarilishini nazorat qilish tizimi.

## 🚀 O'rnatish

### 1. Loyihani yuklab olish
```bash
git clone <repository_url>
cd ishbot
```

### 2. Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Bot token olish
1. [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` komandasini yuboring
3. Bot nomini va username'ini kiriting
4. Bot tokenini oling

### 4. Sozlamalarni o'rnatish

#### Usul 1: .env fayli (tavsiya etiladi)
`.env` faylini yarating:
```env
BOT_TOKEN=your_telegram_bot_token_here
SUPER_ADMIN_TELEGRAM_ID=your_telegram_id_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ishbot
```

**PostgreSQL sozlamalari:**
- `DATABASE_URL` - PostgreSQL database connection string
- Format: `postgresql://user:password@host:port/database`
- Masalan: `postgresql://postgres:postgres@localhost:5432/ishbot`

#### Usul 2: To'g'ridan-to'g'ri
`config.py` faylida `BOT_TOKEN` ni o'zgartiring.

### 5. Super Admin o'rnatish

#### Usul 1: Avtomatik (SUPER_ADMIN_TELEGRAM_ID belgilangan bo'lsa)
Botni ishga tushiring va `/start` komandasini bosing. Siz avtomatik Super Admin bo'lasiz.

#### Usul 2: Skript orqali
```bash
python create_super_admin.py
```

#### Usul 3: Mavjud foydalanuvchini Super Admin qilish
```bash
python setup_admin.py
```

### 6. Botni ishga tushirish
```bash
python main.py
```

## 👥 Foydalanuvchi rollari

### 👑 Super Admin
- Tizim sozlamalari (timezone, jarima, ish soatlari)
- Foydalanuvchi yaratish/bloklash/rol berish
- Vazifa yaratish/taqsimlash
- Vazifani tahrirlash (deadline/start)
- "Tugatdim"ni tasdiqlash yoki rad etish
- Export (CSV/XLSX)
- Barcha tasklarni ko'rish
- Audit logni ko'rish

### 👨‍💼 Admin
- Vazifa yaratish/taqsimlash
- Vazifani tahrirlash (deadline/start)
- "Tugatdim"ni tasdiqlash yoki rad etish
- Export (cheklangan filtr)
- Barcha tasklarni ko'rish (filtrlar bilan)

### 👷 Ishchi
- O'ziga biriktirilgan vazifalarni ko'rish
- Vazifalarni tugatish
- Fayl yuborish

## 📋 Vazifa statuslari

- 📅 **SCHEDULED** - Rejalashtirilgan
- 🔄 **IN_PROGRESS** - Davom etmoqda
- ⏳ **WAITING_APPROVAL** - Tasdiq kutilmoqda
- ✅ **DONE** - Tugatilgan
- ❌ **REJECTED** - Rad etilgan
- 🚨 **OVERDUE** - Muddati o'tgan

## 🎯 Ustuvorlik darajalari

- 🟢 **LOW** - Past
- 🟡 **MEDIUM** - O'rta
- 🟠 **HIGH** - Yuqori
- 🔴 **CRITICAL** - Kritik

## ⏰ Eslatmalar tizimi

- Har 3 soatda aktiv vazifalar bo'yicha eslatma
- 24 soat, 3 soat, 1 soat qolganda deadline eslatmalari
- Muddati o'tganda jarima xabari

## 💰 Jarima tizimi

- Default jarima: 1,000,000 UZS
- Muddati o'tgan vazifalar uchun avtomatik jarima
- Sozlanadigan jarima miqdori

## 📊 Export funksiyalari

- XLSX (Excel) formatida eksport
- CSV formatida eksport
- Sana, ishchi, status bo'yicha filtrlar
- Audit log eksport

## 🔧 Asosiy komandalar

- `/start` - Botni ishga tushirish
- `/help` - Yordam olish
- `/id` - Telegram ID ko'rish (adminlar uchun)

## 📁 Loyiha struktura

```
ishbot/
├── main.py                 # Asosiy bot fayli
├── config.py              # Sozlamalar
├── database.py            # Ma'lumotlar bazasi
├── utils.py               # Yordamchi funksiyalar
├── requirements.txt       # Kerakli kutubxonalar
├── create_super_admin.py  # Super Admin yaratish skripti
├── setup_admin.py         # Super Admin o'rnatish skripti
├── env_example.txt        # .env fayl namunasi
├── handlers/              # Handler fayllari
│   ├── __init__.py
│   ├── base.py           # Asosiy handler
│   ├── start.py          # Start komandalari
│   ├── tasks.py          # Vazifa boshqaruvi
│   ├── users.py          # Foydalanuvchi boshqaruvi
│   ├── export.py         # Export funksiyalari
│   ├── audit.py          # Audit log
│   ├── settings.py       # Sozlamalar
│   └── notifications.py  # Eslatmalar
└── ishbot.db            # SQLite ma'lumotlar bazasi
```

## 🛠 Texnik talablar

- Python 3.8+
- SQLite3
- python-telegram-bot
- pandas
- openpyxl
- python-dotenv
- pytz
- ulid-py

## 📝 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

## 🤝 Yordam

Savollar bo'lsa, muallifga murojaat qiling.

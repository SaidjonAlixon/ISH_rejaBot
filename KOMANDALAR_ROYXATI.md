# 🤖 IshBot - Barcha Komandalar Ro'yxati

## 📋 Asosiy Telegram Komandalar

### `/start`
**Tavsif:** Botni ishga tushirish va asosiy menyuni ko'rsatish
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Yangi foydalanuvchilar uchun registratsiya jarayonini boshlaydi
- Mavjud foydalanuvchilar uchun asosiy menyuni ko'rsatadi
- Foydalanuvchi roliga qarab turli xil menyu ko'rsatadi

### `/help`
**Tavsif:** Bot haqida yordam ma'lumotlari
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Bot funksiyalari haqida ma'lumot
- Foydalanuvchi rollari tushuntirishi
- Vazifa statuslari va ustuvorlik darajalari

### `/id`
**Tavsif:** Telegram ID ko'rsatish
**Ruxsat:** Super Admin va Admin
**Funksiya:**
- Foydalanuvchining Telegram ID sini ko'rsatadi
- Username va telefon raqamini ko'rsatadi

---

## 📝 Vazifa Boshqaruvi (Tasks)

### `create_task`
**Tavsif:** Yangi vazifa yaratish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifa sarlavhasini kiritish
- Vazifa tavsifini kiritish (ixtiyoriy)
- Boshlanish vaqtini belgilash
- Muddati (deadline) belgilash
- Ustuvorlik darajasini tanlash
- Vazifani ishchiga biriktirish

### `tasks_menu`
**Tavsif:** Vazifalar menyusi
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Barcha vazifalar ro'yxati
- Mening vazifalarim
- Faol vazifalar
- Tasdiqlash kutilayotgan vazifalar

### `all_tasks`
**Tavsif:** Barcha vazifalarni ko'rish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Tizimdagi barcha vazifalarni ko'rsatadi
- Filtrlar: status, ustuvorlik, ishchi

### `my_tasks`
**Tavsif:** Mening vazifalarim
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Foydalanuvchiga biriktirilgan vazifalarni ko'rsatadi
- Status bo'yicha filtrlash

### `pending_approval`
**Tavsif:** Tasdiqlash kutilayotgan vazifalar
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- "Tugatdim" deb yuborilgan vazifalarni ko'rsatadi
- Tasdiqlash yoki rad etish imkoniyati

### `active_tasks`
**Tavsif:** Faol vazifalar
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Hozirgi vaqtda davom etayotgan vazifalarni ko'rsatadi

### `completed_tasks`
**Tavsif:** Tugatilgan vazifalar
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Muvaffaqiyatli yakunlangan vazifalarni ko'rsatadi

### `failed_tasks`
**Tavsif:** Muvaffaqiyatsiz vazifalar
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Rad etilgan yoki muvaffaqiyatsiz tugagan vazifalarni ko'rsatadi

### `view_task_{task_id}`
**Tavsif:** Vazifa tafsilotlarini ko'rish
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Vazifa haqida to'liq ma'lumot
- Status, ustuvorlik, muddat
- Biriktirilgan ishchi ma'lumotlari

### `complete_task_{task_id}`
**Tavsif:** Vazifani tugatish
**Ruxsat:** Ishchi (faqat o'z vazifalari uchun)
**Funksiya:**
- Vazifani "Tugatdim" deb belgilash
- Admin tasdiqlashini kutish

### `approve_task_{task_id}`
**Tavsif:** Vazifani tasdiqlash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ishchi tomonidan tugatilgan vazifani tasdiqlash
- Vazifa statusini "BAJARILDI" ga o'zgartirish

### `reject_task_{task_id}`
**Tavsif:** Vazifani rad etish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ishchi tomonidan tugatilgan vazifani rad etish
- Rad etish sababini kiritish
- Vazifani qayta bajarishga yuborish

### `fail_task_{task_id}`
**Tavsif:** Vazifani muvaffaqiyatsiz deb belgilash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifani muvaffaqiyatsiz deb belgilash
- Sababni kiritish

### `extend_task_{task_id}`
**Tavsif:** Vazifa muddatini uzaytirish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifa muddatini yangi sanaga o'zgartirish
- Sababni kiritish

### `priority_{task_id}_{priority}`
**Tavsif:** Vazifa ustuvorligini o'zgartirish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ustuvorlik darajalarini tanlash:
  - 🟢 PAST (LOW)
  - 🟡 ORTA (MEDIUM)
  - 🟠 YUQORI (HIGH)
  - 🔴 KRITIK (CRITICAL)

### `assign_{task_id}_{user_id}`
**Tavsif:** Vazifani ishchiga biriktirish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifani ma'lum ishchiga biriktirish
- Ishchilar ro'yxatidan tanlash

### `resubmit_task_{task_id}`
**Tavsif:** Rad etilgan vazifani qayta yuborish
**Ruxsat:** Ishchi
**Funksiya:**
- Rad etilgan vazifani qayta bajarishga yuborish
- Yangi fayl yuborish imkoniyati

### `start_work`
**Tavsif:** Ish vaqtini boshlash
**Ruxsat:** Ishchi
**Funksiya:**
- Ish vaqtini boshlash
- Kamera oldida rasm tushirish (tasdiqlash uchun)
- Kanalga xabar yuborish

### `end_work`
**Tavsif:** Ish vaqtini tugatish
**Ruxsat:** Ishchi
**Funksiya:**
- Ish vaqtini tugatish
- Kamera oldida rasm tushirish (tasdiqlash uchun)
- Kanalga xabar yuborish

### `search_tasks`
**Tavsif:** Vazifalarni qidirish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifalarni turli parametrlar bo'yicha qidirish
- Filtrlar: sana, ishchi, status

### `edit_tasks`
**Tavsif:** Vazifalarni tahrirlash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Mavjud vazifalarni tahrirlash imkoniyati

### `search_by_worker`
**Tavsif:** Ishchi bo'yicha qidirish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ma'lum ishchiga biriktirilgan vazifalarni ko'rish

### `worker_tasks_{user_id}`
**Tavsif:** Ma'lum ishchining vazifalari
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Tanlangan ishchining barcha vazifalarini ko'rsatadi

### `edit_worker_tasks_{user_id}`
**Tavsif:** Ishchi vazifalarini tahrirlash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ma'lum ishchining vazifalarini tahrirlash

### `edit_task_{task_id}`
**Tavsif:** Vazifani tahrirlash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifa ma'lumotlarini o'zgartirish
- Sarlavha, tavsif, muddat, ustuvorlik

### `request_extension_{task_id}`
**Tavsif:** Muddati uzaytirish so'rovi
**Ruxsat:** Ishchi
**Funksiya:**
- Vazifa muddatini uzaytirish so'rovi yuborish
- Sababni kiritish

### `approve_extension_{task_id}`
**Tavsif:** Muddati uzaytirish so'rovini tasdiqlash
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ishchi tomonidan yuborilgan so'rovni tasdiqlash
- Yangi muddat belgilash
- Izoh qo'shish

### `reject_extension_{task_id}`
**Tavsif:** Muddati uzaytirish so'rovini rad etish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ishchi tomonidan yuborilgan so'rovni rad etish
- Rad etish sababini kiritish

### `skip_description`
**Tavsif:** Vazifa tavsifini o'tkazib yuborish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Vazifa yaratishda tavsifni o'tkazib yuborish
- Keyingi bosqichga o'tish

---

## 👥 Foydalanuvchilar Boshqaruvi (Users)

### `users_menu`
**Tavsif:** Foydalanuvchilar boshqaruvi menyusi
**Ruxsat:** Super Admin
**Funksiya:**
- Foydalanuvchilar bilan bog'liq barcha amallar

### `add_admin`
**Tavsif:** Yangi admin qo'shish
**Ruxsat:** Super Admin
**Funksiya:**
- Yangi admin qo'shish
- Telegram ID yoki username orqali qidirish
- Admin rolini berish

### `add_worker`
**Tavsif:** Yangi ishchi qo'shish
**Ruxsat:** Super Admin
**Funksiya:**
- Yangi ishchi qo'shish
- Telegram ID yoki username orqali qidirish
- Ishchi rolini berish

### `list_users`
**Tavsif:** Foydalanuvchilar ro'yxati
**Ruxsat:** Super Admin
**Funksiya:**
- Barcha foydalanuvchilarni ko'rsatadi
- Filtrlar: rol, faollik holati

### `user_details_{user_id}`
**Tavsif:** Foydalanuvchi tafsilotlari
**Ruxsat:** Super Admin
**Funksiya:**
- Foydalanuvchi haqida to'liq ma'lumot
- Rol, telefon, username
- Faollik holati

### `make_admin_{user_id}`
**Tavsif:** Foydalanuvchini admin qilish
**Ruxsat:** Super Admin
**Funksiya:**
- Mavjud foydalanuvchining rolini Admin ga o'zgartirish

### `make_worker_{user_id}`
**Tavsif:** Foydalanuvchini ishchi qilish
**Ruxsat:** Super Admin
**Funksiya:**
- Mavjud foydalanuvchining rolini Ishchi ga o'zgartirish

### `activate_{user_id}`
**Tavsif:** Foydalanuvchini faollashtirish
**Ruxsat:** Super Admin
**Funksiya:**
- Bloklangan foydalanuvchini faollashtirish

### `deactivate_{user_id}`
**Tavsif:** Foydalanuvchini bloklash
**Ruxsat:** Super Admin
**Funksiya:**
- Foydalanuvchini bloklash (faolsizlashtirish)

---

## 📤 Eksport (Export)

### `export_menu`
**Tavsif:** Eksport menyusi
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ma'lumotlarni eksport qilish imkoniyatlari

### `export_xlsx`
**Tavsif:** XLSX formatida eksport
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Excel formatida fayl yaratish
- Filtrlar: barcha, foydalanuvchi, ishchi

### `export_all_{export_type}`
**Tavsif:** Barcha ma'lumotlarni eksport qilish
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Barcha vazifalarni eksport qilish
- export_type: xlsx, csv

### `export_user_{user_id}_{export_type}`
**Tavsif:** Ma'lum foydalanuvchi bo'yicha eksport
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ma'lum foydalanuvchining vazifalarini eksport qilish

### `export_worker_{user_id}_{export_type}`
**Tavsif:** Ma'lum ishchi bo'yicha eksport
**Ruxsat:** Super Admin, Admin
**Funksiya:**
- Ma'lum ishchining vazifalarini eksport qilish

---

## 📜 Audit Log

### `audit_log`
**Tavsif:** Audit log ko'rish
**Ruxsat:** Super Admin
**Funksiya:**
- Tizimdagi barcha amallar tarixini ko'rish
- Filtrlar: sana, foydalanuvchi, amal turi

### `audit_full_report`
**Tavsif:** To'liq audit hisobot
**Ruxsat:** Super Admin
**Funksiya:**
- Barcha audit loglarni ko'rsatadi
- Batafsil ma'lumotlar

### `export_audit_csv`
**Tavsif:** Audit logni CSV formatida eksport qilish
**Ruxsat:** Super Admin
**Funksiya:**
- Audit loglarni CSV fayl sifatida yuklab olish

---

## ⚙️ Sozlamalar (Settings)

### `settings_menu`
**Tavsif:** Sozlamalar menyusi
**Ruxsat:** Super Admin
**Funksiya:**
- Tashkilot sozlamalarini boshqarish

### `edit_org_name`
**Tavsif:** Tashkilot nomini o'zgartirish
**Ruxsat:** Super Admin
**Funksiya:**
- Tashkilot nomini yangilash

### `edit_timezone`
**Tavsif:** Vaqt mintaqasini o'zgartirish
**Ruxsat:** Super Admin
**Funksiya:**
- Tashkilot vaqt mintaqasini belgilash
- O'zbekiston vaqt mintaqalari

### `timezone_{timezone}`
**Tavsif:** Vaqt mintaqasini tanlash
**Ruxsat:** Super Admin
**Funksiya:**
- Ro'yxatdan vaqt mintaqasini tanlash

### `edit_penalty`
**Tavsif:** Jarima miqdorini o'zgartirish
**Ruxsat:** Super Admin
**Funksiya:**
- Muddati o'tgan vazifalar uchun jarima miqdorini belgilash
- So'mda kiritiladi

### `edit_work_hours`
**Tavsif:** Ish soatlarini o'zgartirish
**Ruxsat:** Super Admin
**Funksiya:**
- Ish boshlanish va tugash vaqtini belgilash
- Format: 09:00 - 18:00

### `edit_reminder`
**Tavsif:** Eslatma sozlamalarini o'zgartirish
**Ruxsat:** Super Admin
**Funksiya:**
- Eslatma intervalini belgilash
- Vaqt birligi: soat yoki minut

### `reminder_unit_{unit}`
**Tavsif:** Eslatma vaqt birligini tanlash
**Ruxsat:** Super Admin
**Funksiya:**
- Vaqt birligini tanlash: soat yoki minut

---

## 🔙 Navigatsiya

### `main_menu`
**Tavsif:** Asosiy menyuga qaytish
**Ruxsat:** Barcha foydalanuvchilar
**Funksiya:**
- Asosiy menyuga qaytish
- Foydalanuvchi roliga qarab menyu ko'rsatadi

---

## 📱 Xabar Turlari

### Matn xabarlari
**Tavsif:** Oddiy matn xabarlari
**Funksiya:**
- Registratsiya jarayonida ma'lumot kiritish
- Vazifa yaratishda ma'lumot kiritish
- Sozlamalarni o'zgartirishda qiymat kiritish

### Kontakt xabarlari
**Tavsif:** Telefon raqami ulashish
**Funksiya:**
- Registratsiya jarayonida telefon raqamini ulashish
- Avtomatik telefon raqamini olish

### Rasm xabarlari
**Tavsif:** Kamera oldida tushilgan rasmlar
**Funksiya:**
- Ish vaqtini boshlashda rasm yuborish
- Ish vaqtini tugatishda rasm yuborish
- Vazifa bajarilganini tasdiqlash

---

## 🎭 Foydalanuvchi Rollari

### 👑 Super Admin
**Ruxsatlar:**
- Barcha funksiyalarga kirish
- Foydalanuvchilar boshqaruvi
- Sozlamalar boshqaruvi
- Audit log ko'rish
- Vazifa yaratish va tahrirlash
- Vazifalarni tasdiqlash/rad etish

### 👨‍💼 Admin
**Ruxsatlar:**
- Vazifa yaratish va tahrirlash
- Vazifalarni tasdiqlash/rad etish
- Eksport funksiyalari
- Vazifalarni ko'rish va qidirish

### 👷 Ishchi
**Ruxsatlar:**
- O'ziga biriktirilgan vazifalarni ko'rish
- Vazifalarni tugatish
- Ish vaqtini boshlash/tugatish
- Muddati uzaytirish so'rovi yuborish

---

## 📊 Vazifa Statuslari

- **📅 SCHEDULED** - Rejalashtirilgan (hali boshlanmagan)
- **🔄 IN_PROGRESS** - Davom etmoqda (ish boshlandi)
- **⏳ WAITING_APPROVAL** - Tasdiqlash kutilmoqda (tugatilgan, admin tasdiqlashini kutmoqda)
- **✅ DONE** - Bajarilgan (tasdiqlangan)
- **❌ REJECTED** - Rad etilgan (admin tomonidan rad etilgan)
- **🚨 OVERDUE** - Muddati o'tgan (muddat o'tib ketgan)

---

## 🎯 Ustuvorlik Darajalari

- **🟢 PAST (LOW)** - Past ustuvorlik
- **🟡 ORTA (MEDIUM)** - O'rta ustuvorlik
- **🟠 YUQORI (HIGH)** - Yuqori ustuvorlik
- **🔴 KRITIK (CRITICAL)** - Kritik ustuvorlik

---

## ⏰ Eslatmalar Tizimi

- **Har 3 soatda** - Faol vazifalar bo'yicha eslatma
- **24 soat qolganda** - Deadline eslatmasi
- **3 soat qolganda** - Deadline eslatmasi
- **1 soat qolganda** - Deadline eslatmasi
- **Muddati o'tganda** - Jarima xabari

---

## 💰 Jarima Tizimi

- **Default jarima:** 1,000,000 UZS
- **Muddati o'tgan vazifalar** uchun avtomatik jarima
- **Sozlanadigan jarima miqdori** (Super Admin tomonidan)

---

## 📝 Eslatmalar

1. Barcha callback query handlerlar inline keyboard tugmalari orqali ishlaydi
2. Vazifa ID lari dinamik ravishda yaratiladi
3. Foydalanuvchi ID lari database dan olinadi
4. Barcha amallar audit logga yoziladi
5. Ruxsatlar foydalanuvchi roliga qarab tekshiriladi

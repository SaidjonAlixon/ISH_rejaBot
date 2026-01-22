from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from config import UserRole, DEFAULT_PENALTY_AMOUNT, DEFAULT_TIMEZONE
from utils import format_penalty_amount
import logging

logger = logging.getLogger(__name__)

class SettingsHandler(BaseHandler):
    def __init__(self, db):
        super().__init__(db)
        self.user_states = {}
    
    async def handle_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sozlamalar menyusi"""
        try:
            user = self.get_user(update)
            
            if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
                await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
                return
            
            # Hozirgi sozlamalarni olish
            settings = self.db.get_org_settings()
            
            if not settings:
                # Agar sozlamalar yo'q bo'lsa, default yaratish
                self.db.create_org_settings("Yangi Tashkilot")
                settings = self.db.get_org_settings()
            
            # Settings tekshiruvi
            if not settings:
                logger.error("Sozlamalar yaratib bo'lmadi!")
                await self.send_message(update, context, "❌ Xatolik: Sozlamalar yaratib bo'lmadi!")
                return
            
            # Default qiymatlar
            org_name = settings.get('org_name', 'Sozlanmagan')
            timezone = settings.get('timezone', 'Asia/Tashkent')
            penalty_amount = settings.get('penalty_amount', 1000000)
            work_hours_start = settings.get('work_hours_start', 9)
            work_hours_end = settings.get('work_hours_end', 18)
            reminder_interval_minutes = settings.get('reminder_interval_minutes', 180)  # Default 3 soat (180 minut)
            
            # Ogohlantirish vaqtini formatlash
            reminder_hours = reminder_interval_minutes // 60
            reminder_mins = reminder_interval_minutes % 60
            if reminder_hours > 0 and reminder_mins > 0:
                reminder_text = f"{reminder_hours} soat {reminder_mins} minut"
            elif reminder_hours > 0:
                reminder_text = f"{reminder_hours} soat"
            else:
                reminder_text = f"{reminder_mins} minut"
            
            text = f"""
⚙️ <b>Tashkilot sozlamalari</b>

🏢 <b>Tashkilot nomi:</b> {org_name}
🌍 <b>Vaqt zonasi:</b> {timezone}
💰 <b>Jarima miqdori:</b> {format_penalty_amount(penalty_amount)}
🕘 <b>Ish soati:</b> {work_hours_start:02d}:00 - {work_hours_end:02d}:00
🔔 <b>Ogohlantirish vaqti:</b> Har {reminder_text}da

Quyidagi sozlamalardan birini tanlang:
            """
            
            keyboard = [
                [InlineKeyboardButton("🏢 Tashkilot nomi", callback_data="edit_org_name")],
                [InlineKeyboardButton("🌍 Vaqt zonasi", callback_data="edit_timezone")],
                [InlineKeyboardButton("💰 Jarima miqdori", callback_data="edit_penalty")],
                [InlineKeyboardButton("🕘 Ish soati", callback_data="edit_work_hours")],
                [InlineKeyboardButton("🔔 Ogohlantirish", callback_data="edit_reminder")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_message(update, context, text, reply_markup)
        except Exception as e:
            logger.error(f"Sozlamalar menyusida xatolik: {e}", exc_info=True)
            await self.send_message(update, context, "❌ Xatolik yuz berdi! Iltimos, qayta urinib ko'ring.")
    
    async def handle_edit_org_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tashkilot nomini tahrirlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        self.user_states[user['id']] = 'editing_org_name'
        
        text = """
🏢 <b>Tashkilot nomini tahrirlash</b>

Yangi tashkilot nomini yuboring:
        """
        
        reply_markup = self.create_back_button("settings_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vaqt zonasi tahrirlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        text = """
🌍 <b>Vaqt zonasi tahrirlash</b>

Vaqt zonasini tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("🇺🇿 Asia/Tashkent", callback_data="timezone_Asia/Tashkent")],
            [InlineKeyboardButton("🇷🇺 Europe/Moscow", callback_data="timezone_Europe/Moscow")],
            [InlineKeyboardButton("🇺🇸 America/New_York", callback_data="timezone_America/New_York")],
            [InlineKeyboardButton("🇬🇧 Europe/London", callback_data="timezone_Europe/London")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="settings_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_penalty(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Jarima miqdorini tahrirlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        self.user_states[user['id']] = 'editing_penalty'
        
        text = """
💰 <b>Jarima miqdorini tahrirlash</b>

Yangi jarima miqdorini UZS da yuboring (faqat raqam):
Masalan: 1000000
        """
        
        reply_markup = self.create_back_button("settings_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_work_hours(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish soatini tahrirlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        # MUHIM: Boshqa holatlarni tozalash (ogohlantirish holatini tozalash)
        if user['id'] in self.user_states:
            old_state = self.user_states.get(user['id'])
            if old_state == 'editing_reminder_value':
                # Ogohlantirish holatini tozalash
                if 'reminder_unit' in context.user_data:
                    del context.user_data['reminder_unit']
                logger.info(f"Ish soati sozlamasiga o'tish: oldingi holat {old_state} tozalandi")
        
        # Avval ish boshlanish vaqtini so'rash
        self.user_states[user['id']] = 'editing_work_start'
        
        text = """
🕘 <b>Ish soatini tahrirlash</b>

Iltimos, ish boshlanish vaqtini yuboring (HH:MM formatida):
Masalan: 09:00
        """
        
        reply_markup = self.create_back_button("settings_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_org_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tashkilot nomi kiritish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'editing_org_name':
            return
        
        org_name = update.message.text.strip()
        
        if not org_name:
            await self.send_message(update, context, "❌ Tashkilot nomi bo'sh bo'lishi mumkin emas!")
            return
        
        # Tashkilot nomini yangilash
        query = "UPDATE org_settings SET org_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM org_settings ORDER BY id DESC LIMIT 1)"
        self.db.execute_update(query, (org_name,))
        
        # Holatni tozalash
        del self.user_states[user['id']]
        
        # Audit log
        self.db.add_audit_log(user['id'], 'SETTINGS_UPDATED', f"Tashkilot nomi yangilandi: {org_name}")
        
        text = f"""
✅ <b>Tashkilot nomi yangilandi!</b>

🏢 <b>Yangi nom:</b> {org_name}
        """
        
        reply_markup = self.create_back_button("settings_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_penalty_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Jarima miqdori kiritish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'editing_penalty':
            return
        
        try:
            penalty_amount = int(update.message.text.strip())
            
            if penalty_amount < 0:
                await self.send_message(update, context, "❌ Jarima miqdori manfiy bo'lishi mumkin emas!")
                return
            
            # Jarima miqdorini yangilash
            query = "UPDATE org_settings SET penalty_amount = ?, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM org_settings ORDER BY id DESC LIMIT 1)"
            self.db.execute_update(query, (penalty_amount,))
            
            # Holatni tozalash
            del self.user_states[user['id']]
            
            # Audit log
            self.db.add_audit_log(user['id'], 'SETTINGS_UPDATED', f"Jarima miqdori yangilandi: {penalty_amount} UZS")
            
            text = f"""
✅ <b>Jarima miqdori yangilandi!</b>

💰 <b>Yangi miqdor:</b> {format_penalty_amount(penalty_amount)}
            """
            
            reply_markup = self.create_back_button("settings_menu")
            await self.send_message(update, context, text, reply_markup)
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Faqat raqam yuboring.")
    
    async def handle_timezone_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vaqt zonasi tanlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        timezone = update.callback_query.data.split('_')[1]
        
        # Vaqt zonasini yangilash
        query = "UPDATE org_settings SET timezone = ?, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM org_settings ORDER BY id DESC LIMIT 1)"
        self.db.execute_update(query, (timezone,))
        
        # Audit log
        self.db.add_audit_log(user['id'], 'SETTINGS_UPDATED', f"Vaqt zonasi yangilandi: {timezone}")
        
        text = f"""
✅ <b>Vaqt zonasi yangilandi!</b>

🌍 <b>Yangi vaqt zonasi:</b> {timezone}
        """
        
        reply_markup = self.create_back_button("settings_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_work_start_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish boshlanish vaqtini kiritish"""
        user = self.get_user(update)
        
        # Holatni qat'iy tekshirish - faqat editing_work_start holatida ishlaydi
        current_state = self.user_states.get(user['id'])
        if current_state != 'editing_work_start':
            logger.debug(f"handle_work_start_input: holat mos kelmaydi. Holat: {current_state}, kutilyapti: editing_work_start")
            return
        
        try:
            time_str = update.message.text.strip()
            
            # Vaqt formatini tekshirish (HH:MM)
            if ':' not in time_str:
                await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 09:00")
                return
            
            parts = time_str.split(':')
            if len(parts) != 2:
                await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 09:00")
                return
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if hour < 0 or hour > 23:
                await self.send_message(update, context, "❌ Soat 0-23 orasida bo'lishi kerak!")
                return
            
            if minute < 0 or minute > 59:
                await self.send_message(update, context, "❌ Daqiqa 0-59 orasida bo'lishi kerak!")
                return
            
            # Ish boshlanish vaqtini saqlash va keyingi bosqichga o'tish
            context.user_data['work_start_hour'] = hour
            context.user_data['work_start_minute'] = minute
            self.user_states[user['id']] = 'editing_work_end'
            
            text = f"""
✅ <b>Ish boshlanish vaqti qabul qilindi:</b> {hour:02d}:{minute:02d}

Iltimos, ish tugash vaqtini yuboring (HH:MM formatida):
Masalan: 18:00
            """
            
            reply_markup = self.create_back_button("settings_menu")
            await self.send_message(update, context, text, reply_markup)
            
        except (ValueError, IndexError):
            await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 09:00")
    
    async def handle_work_end_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish tugash vaqtini kiritish va saqlash"""
        user = self.get_user(update)
        
        # Holatni qat'iy tekshirish - faqat editing_work_end holatida ishlaydi
        current_state = self.user_states.get(user['id'])
        if current_state != 'editing_work_end':
            logger.debug(f"handle_work_end_input: holat mos kelmaydi. Holat: {current_state}, kutilyapti: editing_work_end")
            return
        
        try:
            time_str = update.message.text.strip()
            
            # Vaqt formatini tekshirish (HH:MM)
            if ':' not in time_str:
                await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 18:00")
                return
            
            parts = time_str.split(':')
            if len(parts) != 2:
                await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 18:00")
                return
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if hour < 0 or hour > 23:
                await self.send_message(update, context, "❌ Soat 0-23 orasida bo'lishi kerak!")
                return
            
            if minute < 0 or minute > 59:
                await self.send_message(update, context, "❌ Daqiqa 0-59 orasida bo'lishi kerak!")
                return
            
            # Ish boshlanish vaqtini olish
            start_hour = context.user_data.get('work_start_hour')
            start_minute = context.user_data.get('work_start_minute')
            
            if start_hour is None or start_minute is None:
                await self.send_message(update, context, "❌ Xatolik! Qaytadan boshlang.")
                del self.user_states[user['id']]
                return
            
            # Ish soatini yangilash (faqat soatni saqlaymiz, chunki database struktura shunday)
            # Foydalanuvchi daqiqani ham kiritishi mumkin, lekin biz faqat soatni saqlaymiz
            query = "UPDATE org_settings SET work_hours_start = ?, work_hours_end = ?, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM org_settings ORDER BY id DESC LIMIT 1)"
            self.db.execute_update(query, (start_hour, hour))
            
            # Holatni tozalash
            del self.user_states[user['id']]
            if 'work_start_hour' in context.user_data:
                del context.user_data['work_start_hour']
            if 'work_start_minute' in context.user_data:
                del context.user_data['work_start_minute']
            
            # Audit log (ko'rsatish uchun daqiqani ham qo'shamiz)
            self.db.add_audit_log(user['id'], 'SETTINGS_UPDATED', f"Ish soati yangilandi: {start_hour:02d}:{start_minute:02d} - {hour:02d}:{minute:02d}")
            
            text = f"""
✅ <b>Ish soati yangilandi!</b>

🕘 <b>Yangi ish soati:</b> {start_hour:02d}:{start_minute:02d} - {hour:02d}:{minute:02d}

<i>Eslatma: Database da faqat soat saqlanadi, daqiqa 0 ga tenglashtiriladi.</i>
            """
            
            reply_markup = self.create_back_button("settings_menu")
            await self.send_message(update, context, text, reply_markup)
            
        except (ValueError, IndexError):
            await self.send_message(update, context, "❌ Noto'g'ri format! HH:MM formatida yuboring.\nMasalan: 18:00")
    
    async def handle_edit_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ogohlantirish vaqtini tahrirlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        text = """
🔔 <b>Ogohlantirish vaqtini sozlash</b>

Ishchilarning vazifalari qancha vaqtda qayta yuborilib ogohlantirilsin?

Vaqt birligini tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("⏰ Soat", callback_data="reminder_unit_hours")],
            [InlineKeyboardButton("⏱ Minut", callback_data="reminder_unit_minutes")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="settings_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_reminder_unit_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ogohlantirish vaqti birligini tanlash"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        # Callback query javobini yopish
        if update.callback_query:
            await update.callback_query.answer()
        
        query_data = update.callback_query.data
        unit = query_data.split('_')[-1]  # 'hours' yoki 'minutes'
        
        # MUHIM: Boshqa holatlarni tozalash (ish soati holatlarini tozalash)
        if user['id'] in self.user_states:
            old_state = self.user_states.get(user['id'])
            logger.info(f"Reminder unit tanlash: oldingi holat = {old_state}")
            
            # Ish soati holatlarini tozalash
            if old_state in ['editing_work_start', 'editing_work_end']:
                if 'work_start_hour' in context.user_data:
                    del context.user_data['work_start_hour']
                if 'work_start_minute' in context.user_data:
                    del context.user_data['work_start_minute']
                logger.info(f"Ish soati holatlari tozalandi: {old_state}")
        
        # Ogohlantirish holatini o'rnatish
        context.user_data['reminder_unit'] = unit
        self.user_states[user['id']] = 'editing_reminder_value'
        
        logger.info(f"Reminder unit tanlandi: {unit}, holat: editing_reminder_value, user_id: {user['id']}")
        
        if unit == 'hours':
            text = """
⏰ <b>Ogohlantirish vaqti (Soat)</b>

Har necha soatda ogohlantirish yuborilsin?
Faqat raqam kiriting (masalan: 3)

<i>Masalan: 3 kiritsangiz, har 3 soatda ogohlantirish yuboriladi</i>
            """
        else:
            text = """
⏱ <b>Ogohlantirish vaqti (Minut)</b>

Har necha minutda ogohlantirish yuborilsin?
Faqat raqam kiriting (masalan: 5)

<i>Masalan: 5 kiritsangiz, har 5 minutda ogohlantirish yuboriladi</i>
            """
        
        reply_markup = self.create_back_button("settings_menu")
        # Yangi xabar yuborish (callback query edit qilmaslik)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def handle_reminder_value_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ogohlantirish vaqti qiymatini kiritish"""
        user = self.get_user(update)
        
        # Holatni tekshirish
        current_state = self.user_states.get(user['id'])
        logger.info(f"Reminder value input: holat = {current_state}, user_id = {user['id']}")
        
        if current_state != 'editing_reminder_value':
            logger.warning(f"Noto'g'ri holat: {current_state}, kutilyapti: editing_reminder_value")
            # Agar boshqa holat bo'lsa, uni ignore qilish
            return
        
        try:
            value = int(update.message.text.strip())
            
            if value <= 0:
                await self.send_message(update, context, "❌ Vaqt 0 dan katta bo'lishi kerak!")
                return
            
            unit = context.user_data.get('reminder_unit')
            if not unit:
                await self.send_message(update, context, "❌ Xatolik! Qaytadan boshlang.")
                del self.user_states[user['id']]
                return
            
            # Minutga o'tkazish
            if unit == 'hours':
                reminder_minutes = value * 60
                display_text = f"{value} soat"
            else:
                reminder_minutes = value
                display_text = f"{value} minut"
            
            # Database ga saqlash
            query = "UPDATE org_settings SET reminder_interval_minutes = %s, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM org_settings ORDER BY id DESC LIMIT 1)"
            self.db.execute_update(query, (reminder_minutes,))
            
            # Holatni tozalash
            del self.user_states[user['id']]
            if 'reminder_unit' in context.user_data:
                del context.user_data['reminder_unit']
            
            # Audit log
            self.db.add_audit_log(user['id'], 'SETTINGS_UPDATED', f"Ogohlantirish vaqti yangilandi: {display_text} ({reminder_minutes} minut)")
            
            text = f"""
✅ <b>Ogohlantirish vaqti yangilandi!</b>

🔔 <b>Yangi vaqt:</b> Har {display_text}da

Ishchilarning vazifalari endi har {display_text}da qayta yuborilib ogohlantiriladi.
            """
            
            reply_markup = self.create_back_button("settings_menu")
            await self.send_message(update, context, text, reply_markup)
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Faqat raqam yuboring.")

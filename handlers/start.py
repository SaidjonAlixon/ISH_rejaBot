from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from config import UserRole
import logging
import re

logger = logging.getLogger(__name__)

class StartHandler(BaseHandler):
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start komandasi"""
        user = self.get_user(update)
        
        # Agar foydalanuvchi to'liq registratsiya qilmagan bo'lsa
        if not user.get('full_name') or user.get('full_name') == 'Yangi Foydalanuvchi' or not user.get('phone'):
            # Super Admin uchun ro'yxatdan o'tish jarayonini o'tkazib yuborish
            if user.get('role') == UserRole.SUPER_ADMIN:
                # Super Admin uchun default ma'lumotlar
                self.db.update_user_full_name(user['id'], "Super Admin")
                self.db.update_user_phone(user['id'], "+998000000000")
                # Yangi user object ni olish
                user = self.get_user(update)
            else:
                await self.start_registration(update, context, user)
                return
        
        # Tashkilot sozlamalarini tekshirish
        org_settings = self.db.get_org_settings()
        if not org_settings and user['role'] == UserRole.SUPER_ADMIN:
            # Super Admin uchun tashkilot sozlamalarini yaratish
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        welcome_text = f"""
🤖 <b>IshBot - Vazifa Boshqarish Tizimi</b>

👋 Salom, <b>{user['full_name']}</b>!

🎭 <b>Rolingiz:</b> {self.get_role_name(user['role'])}

📊 <b>Tashkilot:</b> {org_settings['org_name'] if org_settings else 'Sozlanmagan'}

Quyidagi menyudan kerakli funksiyani tanlang:
        """
        
        reply_markup = self.create_main_menu(user['role'])
        await self.send_message(update, context, welcome_text, reply_markup)
        
        # Audit log
        self.db.add_audit_log(user['id'], 'BOT_STARTED', f"Bot ishga tushirildi")
    
    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
        """Registratsiya jarayonini boshlash"""
        welcome_text = """
🤖 <b>Assalomu alaykum, hush kelibsiz!</b>

IshBot - Vazifa Boshqarish Tizimiga xush kelibsiz!

Iltimos, ism va familiyangizni kiriting.
<b>Namuna:</b> Avazbek Avezov
        """
        
        # Foydalanuvchi holatini o'rnatish
        self.user_states = getattr(self, 'user_states', {})
        self.user_states[user['id']] = 'waiting_full_name'
        
        await self.send_message(update, context, welcome_text)
    
    async def handle_full_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ism familiya qabul qilish"""
        user = self.get_user(update)
        full_name = update.message.text.strip()
        
        # Ism familiya formatini tekshirish (kamida 2 so'z)
        if len(full_name.split()) < 2:
            await self.send_message(update, context, 
                "❌ Iltimos, to'liq ism va familiyangizni kiriting.\n<b>Namuna:</b> Avazbek Avezov")
            return
        
        # Ism familiyani saqlash
        self.db.update_user_full_name(user['id'], full_name)
        
        # Telefon raqamini so'rash
        phone_text = f"""
✅ <b>Ism familiya qabul qilindi:</b> {full_name}

📱 Endi telefon raqamingizni ulashing yoki yozib yuboring.
<b>Namuna:</b> +998901234567 yoki 998901234567
        """
        
        # Telefon ulashish tugmasi
        keyboard = [
            [KeyboardButton("📱 Telefon raqamini ulashish", request_contact=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        # Foydalanuvchi holatini o'zgartirish
        self.user_states[user['id']] = 'waiting_phone'
        
        await update.message.reply_text(phone_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Telefon raqami qabul qilish"""
        user = self.get_user(update)
        
        phone = None
        
        # Foydalanuvchi holatini tekshirish
        state = self.user_states.get(user['id'], '')
        
        # Telefon raqami yuborilgan yoki yozilgan
        if update.message.contact:
            phone = update.message.contact.phone_number
        elif update.message.text:
            # Agar tugma matni bo'lsa, uni e'tiborsiz qoldirish
            if update.message.text == "📱 Telefon raqamini ulashish":
                return
            phone = update.message.text.strip()
        
        if not phone:
            await self.send_message(update, context, 
                "❌ Telefon raqami yuborilmadi. Iltimos, qayta urinib ko'ring.")
            return
        
        # Telefon raqami formatini tekshirish va to'g'rilash
        phone = self.validate_phone(phone)
        if not phone:
            await self.send_message(update, context, 
                "❌ Telefon raqami noto'g'ri formatda. Iltimos, qayta yuboring.\n<b>Namuna:</b> +998901234567")
            return
        
        # Telefon raqamini saqlash
        self.db.update_user_phone(user['id'], phone)
        
        # Registratsiya yakunlangan
        await self.complete_registration(update, context, user)
    
    def validate_phone(self, phone: str) -> str:
        """Telefon raqami formatini tekshirish"""
        # Raqamlar va + belgisini qoldirish
        phone = re.sub(r'[^\d+]', '', phone)
        
        # Uzbekiston raqamlari uchun tekshirish
        if phone.startswith('+998'):
            return phone
        elif phone.startswith('998'):
            return '+' + phone
        elif phone.startswith('8') and len(phone) == 13:
            return '+998' + phone[1:]
        elif phone.startswith('9') and len(phone) == 9:
            return '+998' + phone
        else:
            return None
    
    async def complete_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
        """Registratsiyani yakunlash"""
        # Yangilangan foydalanuvchi ma'lumotlarini olish
        updated_user = self.db.get_user_by_telegram_id(user['telegram_id'])
        
        welcome_text = f"""
🎉 <b>Hush kelibsiz!</b>

✅ Registratsiya muvaffaqiyatli yakunlandi!

👤 <b>Ism familiya:</b> {updated_user['full_name']}
📱 <b>Telefon:</b> {updated_user['phone']}
🎭 <b>Rolingiz:</b> {self.get_role_name(updated_user['role'])}

Endi bot funksiyalaridan foydalanishingiz mumkin!
        """
        
        # Klaviatura qaytarish
        from telegram import ReplyKeyboardRemove
        reply_markup = ReplyKeyboardRemove()
        
        # Foydalanuvchi holatini tozalash
        self.user_states.pop(user['id'], None)
        
        # Asosiy menyuni ko'rsatish
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Tashkilot sozlamalarini tekshirish
        org_settings = self.db.get_org_settings()
        if not org_settings and updated_user['role'] == UserRole.SUPER_ADMIN:
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        # Asosiy menyu
        main_menu_text = f"""
📊 <b>Tashkilot:</b> {org_settings['org_name'] if org_settings else 'Sozlanmagan'}

Quyidagi menyudan kerakli funksiyani tanlang:
        """
        
        reply_markup = self.create_main_menu(updated_user['role'])
        await self.send_message(update, context, main_menu_text, reply_markup)
        
        # Audit log
        self.db.add_audit_log(updated_user['id'], 'USER_REGISTERED', 
            f"Registratsiya yakunlandi: {updated_user['full_name']}")
    
    async def handle_phone_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Telefon raqami tanlash"""
        user = self.get_user(update)
        
        if update.message.text == "📱 Telefon raqamini ulashish":
            await self.send_message(update, context, 
                "📱 Telefon raqamingizni ulashing uchun quyidagi tugmani bosing:")
            # Holatni o'zgartirish - contact kutish uchun
            self.user_states[user['id']] = 'waiting_phone_contact'
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yordam komandasi"""
        help_text = """
📖 <b>IshBot Yordam</b>

<b>Asosiy komandalar:</b>
/start - Botni ishga tushirish
/help - Yordam olish
/id - Telegram ID ko'rish

<b>Foydalanuvchi rollari:</b>
👑 <b>Super Admin</b> - To'liq boshqaruv
👨‍💼 <b>Admin</b> - Vazifa boshqaruvi
👷 <b>Ishchi</b> - Vazifalarni bajarish

<b>Vazifa statuslari:</b>
📅 SCHEDULED - Rejalashtirilgan
🔄 IN_PROGRESS - Davom etmoqda
⏳ WAITING_APPROVAL - Tasdiq kutilmoqda
✅ DONE - Tugatilgan
❌ REJECTED - Rad etilgan
🚨 OVERDUE - Muddati o'tgan

<b>Ustuvorlik darajalari:</b>
🟢 LOW - Past
🟡 MEDIUM - O'rta
🟠 HIGH - Yuqori
🔴 CRITICAL - Kritik

Savollar bo'lsa, administratorga murojaat qiling.
        """
        
        reply_markup = self.create_back_button()
        await self.send_message(update, context, help_text, reply_markup)
    
    async def handle_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ID ko'rsatish komandasi"""
        user = self.get_user(update)
        
        # Barcha foydalanuvchilar o'z ID sini ko'ra oladi
        
        id_text = f"""
🆔 <b>Telegram ID ma'lumotlari</b>

👤 <b>Sizning ID:</b> <code>{update.effective_user.id}</code>
📱 <b>Username:</b> @{update.effective_user.username or 'Yoq'}
📞 <b>Telefon:</b> {user.get('phone', 'Kiritilmagan')}
        """
        
        reply_markup = self.create_back_button()
        await self.send_message(update, context, id_text, reply_markup)
    
    def get_role_name(self, role: str) -> str:
        """Rol nomini olish"""
        role_names = {
            UserRole.SUPER_ADMIN: "👑 Super Admin",
            UserRole.ADMIN: "👨‍💼 Admin", 
            UserRole.WORKER: "👷 Ishchi"
        }
        return role_names.get(role, "❓ Noma'lum")

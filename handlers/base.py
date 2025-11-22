from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from config import UserRole
import logging

logger = logging.getLogger(__name__)

class BaseHandler:
    def __init__(self, db: Database):
        self.db = db
    
    def get_user(self, update: Update) -> dict:
        """Foydalanuvchini olish"""
        user = update.effective_user
        db_user = self.db.get_user_by_telegram_id(user.id)
        
        if not db_user:
            # Yangi foydalanuvchi yaratish
            full_name = "Yangi Foydalanuvchi"
            
            # Super Admin ID tekshirish
            from config import SUPER_ADMIN_TELEGRAM_ID
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Checking SUPER_ADMIN_TELEGRAM_ID: {SUPER_ADMIN_TELEGRAM_ID} (type: {type(SUPER_ADMIN_TELEGRAM_ID)})")
            logger.info(f"User ID: {user.id} (type: {type(user.id)})")
            
            role = UserRole.SUPER_ADMIN if SUPER_ADMIN_TELEGRAM_ID and str(user.id) == str(SUPER_ADMIN_TELEGRAM_ID) else UserRole.WORKER
            logger.info(f"Assigned role: {role}")
            
            db_user_id = self.db.create_user(
                telegram_id=user.id,
                full_name=full_name,
                username=user.username,
                role=role
            )
            # Yangi yaratilgan foydalanuvchini olish
            db_user = self.db.get_user_by_telegram_id(user.id)
            self.db.add_audit_log(db_user['id'], 'USER_REGISTERED', f"Yangi foydalanuvchi yaratildi (Rol: {role})")
        
        return db_user
    
    def check_permission(self, user: dict, required_roles: list) -> bool:
        """Ruxsatni tekshirish"""
        return user['role'] in required_roles
    
    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                    text: str, reply_markup: InlineKeyboardMarkup = None):
        """Xabar yuborish"""
        try:
            # Xabar uzunligini tekshirish (Telegram limiti: 4096 belgi)
            if len(text) > 4000:
                text = text[:3950] + "\n\n... (xabar qisqartirildi)"
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Xabar yuborishda xatolik: {e}")
    
    def create_main_menu(self, user_role: str) -> InlineKeyboardMarkup:
        """Asosiy menyu yaratish"""
        if user_role == UserRole.SUPER_ADMIN:
            keyboard = [
                [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_menu")],
                [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings_menu")],
                [InlineKeyboardButton("📤 Eksport", callback_data="export_menu")],
                [InlineKeyboardButton("📜 Audit log", callback_data="audit_log")],
                [InlineKeyboardButton("➕ Vazifa yaratish", callback_data="create_task")],
                [InlineKeyboardButton("📋 Vazifalar", callback_data="tasks_menu")]
            ]
        elif user_role == UserRole.ADMIN:
            keyboard = [
                [InlineKeyboardButton("➕ Vazifa yaratish", callback_data="create_task")],
                [InlineKeyboardButton("📋 Vazifalar", callback_data="tasks_menu")]
            ]
        else:  # WORKER
            keyboard = [
                [InlineKeyboardButton("🧾 Mening vazifalarim", callback_data="my_tasks")],
                [InlineKeyboardButton("▶️ Ish vaqtim boshladim", callback_data="start_work")],
                [InlineKeyboardButton("✅ Ish vaqtim tugadi", callback_data="end_work")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_back_button(self, callback_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Orqaga qaytish tugmasi"""
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=callback_data)]]
        return InlineKeyboardMarkup(keyboard)

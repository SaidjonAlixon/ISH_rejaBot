from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
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
            
            # Super Admin ID tekshirish (bir nechta ID larni qo'llab-quvvatlash)
            from config import SUPER_ADMIN_TELEGRAM_IDS
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Checking SUPER_ADMIN_TELEGRAM_IDS: {SUPER_ADMIN_TELEGRAM_IDS}")
            logger.info(f"User ID: {user.id} (type: {type(user.id)})")
            
            # Foydalanuvchi ID si ro'yxatda bor-yo'qligini tekshirish
            role = UserRole.SUPER_ADMIN if user.id in SUPER_ADMIN_TELEGRAM_IDS else UserRole.WORKER
            logger.info(f"Assigned role: {role}")
            
            db_user_id = self.db.create_user(
                telegram_id=user.id,
                full_name=full_name,
                username=user.username,
                role=role
            )
            # Yangi yaratilgan foydalanuvchini olish
            db_user = self.db.get_user_by_telegram_id(user.id)
            
            # Agar foydalanuvchi hali ham topilmasa, xatolik
            if not db_user:
                logger.error(f"Foydalanuvchi yaratildi (ID: {db_user_id}), lekin keyin topilmadi!")
                # Qayta urinish
                db_user = self.db.get_user_by_id(db_user_id)
                if not db_user:
                    raise Exception(f"Foydalanuvchi yaratib bo'lmadi: telegram_id={user.id}")
            
            # Audit log
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
        except BadRequest as e:
            # "Message is not modified" xatosini ignore qilish
            if "message is not modified" in str(e).lower():
                logger.debug(f"Xabar o'zgarishsiz: {e}")
            else:
                logger.error(f"Xabar yuborishda xatolik: {e}")
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
                [InlineKeyboardButton("📋 Vazifalar menyusi", callback_data="worker_tasks_menu")],
                [InlineKeyboardButton("📊 Mening statistikam", callback_data="worker_stats")],
                [InlineKeyboardButton("▶️ Ish vaqtim boshladim", callback_data="start_work")],
                [InlineKeyboardButton("✅ Ish vaqtim tugadi", callback_data="end_work")],
                [InlineKeyboardButton("👤 Mening ma'lumotlarim", callback_data="worker_profile")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_back_button(self, callback_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Orqaga qaytish tugmasi"""
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=callback_data)]]
        return InlineKeyboardMarkup(keyboard)

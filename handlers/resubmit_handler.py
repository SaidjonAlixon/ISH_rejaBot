from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import UserRole
from utils import format_datetime, get_uzbek_time
import logging

logger = logging.getLogger(__name__)

class ResubmitHandler:
    def __init__(self, db):
        self.db = db
    
    def get_user(self, update: Update):
        """Foydalanuvchini olish"""
        telegram_id = update.effective_user.id
        user = self.db.get_user_by_telegram_id(telegram_id)
        if not user:
            # Agar foydalanuvchi topilmasa, yangi yaratish
            user_id = self.db.create_user(
                telegram_id=telegram_id,
                full_name=update.effective_user.full_name or "Noma'lum",
                username=update.effective_user.username,
                role='WORKER'
            )
            user = self.db.get_user_by_id(user_id)
        return user
    
    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
        """Xabar yuborish"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    
    async def handle_resubmit_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani qayta yuborish"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            return
        
        # Ruxsat tekshirish
        if user['role'] != UserRole.WORKER or task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifa sizga tegishli emas!")
            return
        
        # Qayta yuborish imkoniyatini tekshirish
        if not self.db.can_resubmit_task(task_id):
            await self.send_message(update, context, "❌ Bu vazifani qayta yuborish imkoniyati tugagan!")
            return
        
        # Statusni TASDIQLASH_KUTILMOQDA ga o'zgartirish
        self.db.update_task_status(task_id, 'TASDIQLASH_KUTILMOQDA')
        
        # Audit log
        resubmit_count = self.db.get_task_resubmit_count(task_id)
        self.db.add_audit_log(user['id'], 'TASK_RESUBMITTED', f"Vazifa qayta yuborildi: {task['title']} (Qayta yuborish: {resubmit_count + 1}/3)")
        
        # Admin'larga xabar yuborish
        await self.notify_admins_task_resubmitted(task, user, context)
        
        text = f"""
🔄 <b>Vazifa qayta yuborildi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Qayta yuboruvchi:</b> {user['full_name']}
📊 <b>Qayta yuborish soni:</b> {resubmit_count + 1}/3
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Admin'lar vazifani qayta ko'rib chiqadi.
        """
        
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Orqaga", callback_data="my_tasks")
        ]])
        await self.send_message(update, context, text, reply_markup)
    
    async def notify_admins_task_resubmitted(self, task, worker, context: ContextTypes.DEFAULT_TYPE):
        """Admin'larga vazifa qayta yuborilganini xabar qilish"""
        try:
            # Admin'larni olish
            admins = self.db.get_users_by_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
            
            for admin in admins:
                notification_text = f"""
🔄 <b>Vazifa qayta yuborildi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Ishchi:</b> {worker['full_name']}
📊 <b>Qayta yuborish soni:</b> {self.db.get_task_resubmit_count(task['id']) + 1}/3
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Iltimos, vazifani qayta ko'rib chiqing va tasdiqlang yoki rad eting.
                """
                
                keyboard = [
                    [
                        InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task['id']}")
                    ],
                    [
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_task_{task['id']}"),
                        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_task_{task['id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=admin['telegram_id'],
                    text=notification_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            logger.info(f"Qayta yuborish xabari yuborildi {len(admins)} ta admin'ga")
            
        except Exception as e:
            logger.error(f"Admin'larga qayta yuborish xabari yuborishda xatolik: {e}")

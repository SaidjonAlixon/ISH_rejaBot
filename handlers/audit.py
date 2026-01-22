from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from config import UserRole
from utils import format_datetime
import logging

logger = logging.getLogger(__name__)

class AuditHandler(BaseHandler):
    def __init__(self, db):
        super().__init__(db)
    
    async def handle_audit_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Audit log ko'rish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        # Audit loglarni olish
        logs = self.db.get_audit_logs(limit=50)
        
        if not logs:
            text = "📝 Audit log bo'sh."
            reply_markup = self.create_back_button("main_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"📜 <b>Audit log</b> (So'nggi {len(logs)} ta)\n\n"
        
        for i, log in enumerate(logs, 1):
            action_emoji = self.get_action_emoji(log['action'])
            text += f"""
{i}. {action_emoji} <b>{log['action']}</b>
👤 <b>Foydalanuvchi:</b> {log['full_name']} ({log['role']})
📅 <b>Vaqt:</b> {format_datetime(log['created_at'])}
📝 <b>Tafsilot:</b> {log['details'] or 'Yoq'}

"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yangilash", callback_data="audit_log")],
            [InlineKeyboardButton("📊 To'liq hisobot", callback_data="audit_full_report")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_audit_full_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """To'liq audit hisoboti"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        # Barcha audit loglarni olish
        logs = self.db.get_audit_logs(limit=1000)
        
        if not logs:
            text = "📝 Audit log bo'sh."
            reply_markup = self.create_back_button("audit_log")
            await self.send_message(update, context, text, reply_markup)
            return
        
        # Statistikalar
        total_actions = len(logs)
        action_counts = {}
        user_counts = {}
        
        for log in logs:
            action_counts[log['action']] = action_counts.get(log['action'], 0) + 1
            user_counts[log['full_name']] = user_counts.get(log['full_name'], 0) + 1
        
        # Eng ko'p amal qilgan foydalanuvchi
        most_active_user = max(user_counts.items(), key=lambda x: x[1])
        
        # Eng ko'p qilingan amal
        most_common_action = max(action_counts.items(), key=lambda x: x[1])
        
        text = f"""
📊 <b>To'liq Audit Hisoboti</b>

📈 <b>Umumiy statistikalar:</b>
• Jami amallar: {total_actions}
• Eng faol foydalanuvchi: {most_active_user[0]} ({most_active_user[1]} ta amal)
• Eng ko'p qilingan amal: {most_common_action[0]} ({most_common_action[1]} marta)

📋 <b>Amallar bo'yicha statistikalar:</b>
"""
        
        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            emoji = self.get_action_emoji(action)
            text += f"• {emoji} {action}: {count} marta\n"
        
        text += f"\n👥 <b>Foydalanuvchilar bo'yicha statistikalar:</b>\n"
        
        for user_name, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            text += f"• {user_name}: {count} ta amal\n"
        
        keyboard = [
            [InlineKeyboardButton("📄 CSV eksport", callback_data="export_audit_csv")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="audit_log")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_export_audit_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Audit log CSV eksport"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        try:
            # Audit loglarni olish
            logs = self.db.get_audit_logs(limit=10000)
            
            if not logs:
                await self.send_message(update, context, "📝 Eksport qilish uchun ma'lumotlar yo'q!")
                return
            
            # CSV ma'lumotlarini tayyorlash
            csv_data = "Vaqt,Foydalanuvchi,Rol,Amal,Tafsilot\n"
            
            for log in logs:
                csv_data += f'"{format_datetime(log["created_at"])}","{log["full_name"]}","{log["role"]}","{log["action"]}","{log["details"] or ""}"\n'
            
            # Faylni yuborish
            filename = f"audit_log_{format_datetime(logs[0]['created_at'], '%Y%m%d_%H%M%S')}.csv"
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=csv_data.encode('utf-8-sig'),
                filename=filename,
                caption=f"📜 <b>Audit log eksport tayyor!</b>\n\n📁 <b>Fayl:</b> {filename}\n📊 <b>Jami amallar:</b> {len(logs)}"
            )
            
            # Audit log
            self.db.add_audit_log(user['id'], 'AUDIT_EXPORTED', f"Audit log CSV formatida eksport qilindi")
            
        except Exception as e:
            logger.error(f"Audit log eksport qilishda xatolik: {e}")
            await self.send_message(update, context, "❌ Eksport qilishda xatolik yuz berdi!")
    
    def get_action_emoji(self, action: str) -> str:
        """Amal uchun emoji"""
        action_emojis = {
            'USER_REGISTERED': '👤',
            'USER_ROLE_UPDATED': '🔄',
            'USER_ROLE_CHANGED': '🔄',
            'USER_STATUS_CHANGED': '⚡',
            'TASK_CREATED': '➕',
            'TASK_COMPLETED': '✅',
            'TASK_APPROVED': '👍',
            'TASK_REJECTED': '👎',
            'TASK_UPDATED': '📝',
            'PENALTY_ADDED': '💰',
            'EXPORT_ALL': '📤',
            'EXPORT_CSV': '📄',
            'EXPORT_XLSX': '📊',
            'AUDIT_EXPORTED': '📜',
            'BOT_STARTED': '🚀',
            'SETTINGS_UPDATED': '⚙️'
        }
        return action_emojis.get(action, '📝')

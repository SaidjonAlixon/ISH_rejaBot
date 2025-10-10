import logging
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import Database
from handlers.start import StartHandler
from handlers.tasks import TaskHandler
from handlers.users import UserHandler
from handlers.export import ExportHandler
from handlers.audit import AuditHandler
from handlers.settings import SettingsHandler
from handlers.notifications import NotificationHandler
from config import BOT_TOKEN
import os

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class IshBot:
    def __init__(self):
        self.db = Database()
        self.start_handler = StartHandler(self.db)
        self.task_handler = TaskHandler(self.db)
        self.user_handler = UserHandler(self.db)
        self.export_handler = ExportHandler(self.db)
        self.audit_handler = AuditHandler(self.db)
        self.settings_handler = SettingsHandler(self.db)
        self.notification_handler = NotificationHandler(self.db, None)
        
        # Bot application yaratish
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlerlarni qo'shish
        self.setup_handlers()
        
        # Notification handler uchun bot instance
        self.notification_handler.bot = self.application.bot
    
    def setup_handlers(self):
        """Handlerlarni sozlash"""
        
        # Komanda handlerlari
        self.application.add_handler(CommandHandler("start", self.start_handler.handle_start))
        self.application.add_handler(CommandHandler("help", self.start_handler.handle_help))
        self.application.add_handler(CommandHandler("id", self.start_handler.handle_id))
        
        # Callback query handlerlari
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Message handlerlari
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
    
    async def handle_callback_query(self, update, context):
        """Callback querylarni boshqarish"""
        query = update.callback_query
        data = query.data
        
        try:
            if data == "main_menu":
                await self.start_handler.handle_start(update, context)
            
            # Task handlers
            elif data == "create_task":
                await self.task_handler.handle_create_task(update, context)
            elif data == "tasks_menu":
                await self.task_handler.handle_tasks_menu(update, context)
            elif data == "all_tasks":
                await self.task_handler.handle_all_tasks(update, context)
            elif data == "pending_approval":
                await self.task_handler.handle_pending_approval(update, context)
            elif data == "my_tasks":
                await self.task_handler.handle_my_tasks(update, context)
            elif data == "active_tasks":
                await self.task_handler.handle_active_tasks(update, context)
            elif data == "completed_tasks":
                await self.task_handler.handle_completed_tasks(update, context)
            elif data == "failed_tasks":
                await self.task_handler.handle_failed_tasks(update, context)
            elif data.startswith("view_task_"):
                await self.task_handler.handle_view_task(update, context)
            elif data.startswith("complete_task_"):
                await self.task_handler.handle_complete_task(update, context)
            elif data.startswith("approve_task_"):
                await self.task_handler.handle_approve_task(update, context)
            elif data.startswith("reject_task_"):
                await self.task_handler.handle_reject_task(update, context)
            elif data.startswith("fail_task_"):
                await self.task_handler.handle_fail_task(update, context)
            elif data.startswith("extend_task_"):
                await self.task_handler.handle_extend_task(update, context)
            elif data.startswith("priority_"):
                await self.task_handler.handle_task_priority(update, context)
            elif data.startswith("assign_"):
                await self.task_handler.handle_task_assign(update, context)
            elif data.startswith("resubmit_task_"):
                await self.task_handler.resubmit_handler.handle_resubmit_task(update, context)
            
            # Admin search and edit handlers
            elif data == "search_tasks":
                await self.task_handler.handle_search_tasks(update, context)
            elif data == "edit_tasks":
                await self.task_handler.handle_edit_tasks(update, context)
            elif data == "search_by_worker":
                await self.task_handler.handle_search_by_worker(update, context)
            elif data.startswith("worker_tasks_"):
                await self.task_handler.handle_worker_tasks(update, context)
            elif data == "select_worker_tasks":
                await self.task_handler.handle_select_worker_tasks(update, context)
            elif data.startswith("edit_worker_tasks_"):
                await self.task_handler.handle_edit_worker_tasks(update, context)
            elif data.startswith("edit_task_"):
                await self.task_handler.handle_edit_task(update, context)
            elif data.startswith("extend_task_"):
                await self.task_handler.handle_extend_task(update, context)
            elif data.startswith("fail_task_"):
                await self.task_handler.handle_fail_task(update, context)
            elif data.startswith("request_extension_"):
                await self.task_handler.handle_request_extension(update, context)
            elif data.startswith("approve_extension_"):
                await self.task_handler.handle_approve_extension(update, context)
            elif data.startswith("reject_extension_"):
                await self.task_handler.handle_reject_extension(update, context)
            
            elif data == "skip_description":
                # Tavsifni o'tkazib yuborish
                user = self.start_handler.get_user(update)
                self.task_handler.user_states[user['id']] = 'task_start_time'
                await self.task_handler.send_message(
                    update, context, 
                    "📅 Boshlanish vaqtini yuboring (DD.MM.YYYY HH:MM formatida):"
                )
            
            # User handlers
            elif data == "users_menu":
                await self.user_handler.handle_users_menu(update, context)
            elif data == "add_admin":
                await self.user_handler.handle_add_admin(update, context)
            elif data == "add_worker":
                await self.user_handler.handle_add_worker(update, context)
            elif data == "list_users":
                await self.user_handler.handle_list_users(update, context)
            elif data.startswith("user_details_"):
                await self.user_handler.handle_user_details(update, context)
            elif data.startswith("make_admin_") or data.startswith("make_worker_"):
                await self.user_handler.handle_change_role(update, context)
            elif data.startswith("activate_") or data.startswith("deactivate_"):
                await self.user_handler.handle_toggle_active(update, context)
            
            # Export handlers
            elif data == "export_menu":
                await self.export_handler.handle_export_menu(update, context)
            elif data == "export_xlsx":
                await self.export_handler.handle_export_xlsx(update, context)
            elif data.startswith("export_all_"):
                await self.export_handler.handle_export_all(update, context)
            elif data.startswith("export_user_"):
                await self.export_handler.handle_export_user(update, context)
            elif data.startswith("export_worker_"):
                # Ishchi bo'yicha eksport
                user_id = int(data.split('_')[2])
                export_type = data.split('_')[3]
                tasks = self.export_handler.get_tasks_by_user(user_id)
                file_data = self.export_handler.create_xlsx_export(tasks)
                filename = f"ishchi_vazifalar_{user_id}_{update.effective_user.id}.xlsx"
                await self.export_handler.send_file(update, context, file_data, filename, export_type)
            
            # Audit handlers
            elif data == "audit_log":
                await self.audit_handler.handle_audit_log(update, context)
            elif data == "audit_full_report":
                await self.audit_handler.handle_audit_full_report(update, context)
            elif data == "export_audit_csv":
                await self.audit_handler.handle_export_audit_csv(update, context)
            
            # Settings handlers
            elif data == "settings_menu":
                await self.settings_handler.handle_settings_menu(update, context)
            elif data == "edit_org_name":
                await self.settings_handler.handle_edit_org_name(update, context)
            elif data == "edit_timezone":
                await self.settings_handler.handle_edit_timezone(update, context)
            elif data == "edit_penalty":
                await self.settings_handler.handle_edit_penalty(update, context)
            elif data == "edit_work_hours":
                await self.settings_handler.handle_edit_work_hours(update, context)
            elif data.startswith("timezone_"):
                await self.settings_handler.handle_timezone_selection(update, context)
            elif data.startswith("work_hours_"):
                await self.settings_handler.handle_work_hours_selection(update, context)
            
            else:
                await query.answer("❌ Noma'lum buyruq!")
        
        except Exception as e:
            logger.error(f"Callback query xatoligi: {e}")
            await query.answer("❌ Xatolik yuz berdi!")
    
    async def handle_message(self, update, context):
        """Matn xabarlarini boshqarish"""
        user = self.start_handler.get_user(update)
        
        # Registratsiya holatini tekshirish
        if hasattr(self.start_handler, 'user_states') and user['id'] in self.start_handler.user_states:
            state = self.start_handler.user_states[user['id']]
            
            if state == 'waiting_full_name':
                await self.start_handler.handle_full_name_input(update, context)
            elif state in ['waiting_phone', 'waiting_phone_text', 'waiting_phone_contact']:
                await self.start_handler.handle_phone_input(update, context)
            elif update.message.text == "📱 Telefon raqamini ulashish":
                await self.start_handler.handle_phone_choice(update, context)
        
        # Foydalanuvchi holatini tekshirish
        elif user['id'] in self.task_handler.user_states:
            state = self.task_handler.user_states[user['id']]
            
            if state == 'creating_task':
                await self.task_handler.handle_task_title(update, context)
            elif state == 'task_description':
                await self.task_handler.handle_task_description(update, context)
            elif state == 'task_start_time':
                await self.task_handler.handle_task_start_time(update, context)
            elif state == 'task_deadline':
                await self.task_handler.handle_task_deadline(update, context)
            elif state.startswith('extend_task_'):
                await self.task_handler.handle_extend_deadline(update, context)
            elif state.startswith('extending_deadline_'):
                await self.task_handler.handle_deadline_extension(update, context)
            elif state == 'requesting_extension':
                await self.task_handler.handle_extension_reason(update, context)
            elif state.startswith('approve_extension_'):
                await self.task_handler.handle_extension_time_input(update, context)
            elif state.startswith('new_deadline_'):
                await self.task_handler.handle_extension_comment_input(update, context)
            elif state.startswith('reject_extension_'):
                await self.task_handler.handle_rejection_reason_input(update, context)
        
        elif user['id'] in self.user_handler.user_states:
            state = self.user_handler.user_states[user['id']]
            
            if state in ['adding_admin', 'adding_worker']:
                await self.user_handler.handle_user_identifier(update, context)
        
        elif user['id'] in self.settings_handler.user_states:
            state = self.settings_handler.user_states[user['id']]
            
            if state == 'editing_org_name':
                await self.settings_handler.handle_org_name_input(update, context)
            elif state == 'editing_penalty':
                await self.settings_handler.handle_penalty_input(update, context)
        
        else:
            # Oddiy xabar
            await update.message.reply_text(
                "🤖 Bot ishlamoqda. /start komandasini bosing."
            )
    
    async def handle_contact(self, update, context):
        """Contact xabarlarini boshqarish"""
        user = self.start_handler.get_user(update)
        
        # Registratsiya holatini tekshirish
        if hasattr(self.start_handler, 'user_states') and user['id'] in self.start_handler.user_states:
            state = self.start_handler.user_states[user['id']]
            
            if state in ['waiting_phone', 'waiting_phone_text', 'waiting_phone_contact']:
                await self.start_handler.handle_phone_input(update, context)
    
    async def start_bot(self):
        """Botni ishga tushirish"""
        logger.info("Bot ishga tushmoqda...")
        
        # Botni ishga tushirish
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Notification handler ni ishga tushirish
        notification_task = asyncio.create_task(self.notification_handler.start_notifications())
        
        logger.info("Bot ishga tushdi!")
        
        # Botni ishga tushirishni kutish
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Bot to'xtatilmoqda...")
        finally:
            # Notification handler ni to'xtatish
            await self.notification_handler.stop_notifications()
            notification_task.cancel()
            
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

def main():
    """Asosiy funksiya"""
    # Bot tokenini tekshirish
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN sozlanmagan! .env faylini yarating va BOT_TOKEN qo'shing.")
        return
    
    # Botni ishga tushirish
    bot = IshBot()
    asyncio.run(bot.start_bot())

if __name__ == "__main__":
    main()

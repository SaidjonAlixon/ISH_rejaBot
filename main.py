import logging
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
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

# Debug uchun environment variables ni tekshirish
from config import SUPER_ADMIN_TELEGRAM_IDS
logger.info(f"SUPER_ADMIN_TELEGRAM_IDS loaded: {SUPER_ADMIN_TELEGRAM_IDS} (count: {len(SUPER_ADMIN_TELEGRAM_IDS)})")

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
        
        # Notification handler uchun post_init va post_stop
        async def post_init(app):
            """Application ishga tushgandan keyin ishlaydi"""
            self.notification_handler.bot = app.bot
            notification_task = asyncio.create_task(self.notification_handler.start_notifications())
            app.bot_data['notification_task'] = notification_task
            logger.info("Bot ishga tushdi!")
        
        async def post_stop(app):
            """Application to'xtatilganda ishlaydi"""
            if 'notification_task' in app.bot_data:
                await self.notification_handler.stop_notifications()
                app.bot_data['notification_task'].cancel()
                logger.info("Notification handler to'xtatildi")
        
        # Bot application yaratish
        self.application = Application.builder().token(BOT_TOKEN).post_init(post_init).post_stop(post_stop).build()
        
        # Error handler qo'shish
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Xatolarni boshqarish"""
            error = context.error
            error_str = str(error) if error else ""
            
            # Conflict xatosi - boshqa bot instance ishlamoqda (bu odatda vaqtincha)
            if "Conflict" in error_str or "terminated by other getUpdates" in error_str:
                logger.warning("⚠️ Conflict xatosi: Boshqa bot instance ishlamoqda. Bu odatda vaqtincha xato va o'z-o'zidan hal bo'ladi.")
                return  # Xatoni ignore qilish
            
            # InvalidToken xatosi - bot token noto'g'ri
            if "Unauthorized" in error_str or "InvalidToken" in error_str:
                logger.error("❌ Bot token noto'g'ri yoki o'chirilgan! .env faylida BOT_TOKEN ni tekshiring.")
                return  # Xatoni ignore qilish, lekin bot to'xtaydi
            
            # Boshqa xatolarni log qilish
            logger.error(f"Xatolik yuz berdi: {error}", exc_info=error)
        
        # Error handler qo'shish
        self.application.add_error_handler(error_handler)
        
        # Handlerlarni qo'shish
        self.setup_handlers()
    
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
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
    
    async def handle_callback_query(self, update, context):
        """Callback querylarni boshqarish"""
        query = update.callback_query
        
        # Callback query tekshiruvi
        if not query:
            logger.error("Callback query None!")
            return
        
        # Callback query javobini yopish (loading ko'rsatkichini olib tashlash)
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Callback query answer xatosi: {e}")
        
        data = query.data
        
        # Data tekshiruvi
        if not data:
            logger.error("Callback query data None!")
            await query.answer("❌ Xatolik: Ma'lumot topilmadi!")
            return
        
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
            elif data == "start_work":
                await self.task_handler.handle_start_work(update, context)
            elif data == "end_work":
                await self.task_handler.handle_end_work(update, context)
            elif data == "worker_tasks_menu":
                await self.task_handler.handle_worker_tasks_menu(update, context)
            elif data == "worker_pending_tasks":
                await self.task_handler.handle_worker_pending_tasks(update, context)
            elif data == "worker_stats":
                await self.task_handler.handle_worker_stats(update, context)
            elif data == "worker_profile":
                await self.task_handler.handle_worker_profile(update, context)
            
            # Admin search and edit handlers
            elif data == "search_tasks":
                await self.task_handler.handle_search_tasks(update, context)
            elif data == "edit_tasks":
                await self.task_handler.handle_edit_tasks(update, context)
            elif data == "search_by_worker":
                await self.task_handler.handle_search_by_worker(update, context)
            elif data == "search_by_date":
                await self.task_handler.handle_search_by_date(update, context)
            elif data == "search_by_status":
                await self.task_handler.handle_search_by_status(update, context)
            elif data.startswith("search_status_"):
                # Status bo'yicha qidirish natijalari
                status = data.replace("search_status_", "")
                tasks = self.export_handler.get_tasks_by_status(status)
                if tasks:
                    text = f"📊 <b>Status: {status}</b> ({len(tasks)} ta vazifa)\n\n"
                    for i, task in enumerate(tasks[:10], 1):
                        text += f"{i}. {task['title']}\n"
                    if len(tasks) > 10:
                        text += f"\n... va yana {len(tasks) - 10} ta vazifa"
                    reply_markup = self.task_handler.create_back_button("search_tasks")
                    await self.task_handler.send_message(update, context, text, reply_markup)
                else:
                    await self.task_handler.send_message(update, context, f"❌ {status} statusidagi vazifalar topilmadi.", self.task_handler.create_back_button("search_tasks"))
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
            elif data == "edit_roles":
                await self.user_handler.handle_edit_roles(update, context)
            
            # Export handlers
            elif data == "export_menu":
                await self.export_handler.handle_export_menu(update, context)
            elif data == "export_xlsx":
                await self.export_handler.handle_export_xlsx(update, context)
            elif data.startswith("export_all_"):
                await self.export_handler.handle_export_all(update, context)
            elif data.startswith("export_user_"):
                await self.export_handler.handle_export_user(update, context)
            elif data.startswith("export_status_"):
                # Status bo'yicha eksport
                parts = data.split('_')
                if len(parts) >= 3:
                    status = parts[2]  # SCHEDULED, IN_PROGRESS, etc.
                    export_type = parts[3] if len(parts) > 3 else 'xlsx'
                    tasks = self.export_handler.get_tasks_by_status(status)
                    if tasks:
                        file_data = self.export_handler.create_xlsx_export(tasks)
                        filename = f"vazifalar_{status}_{update.effective_user.id}.xlsx"
                        await self.export_handler.send_file(update, context, file_data, filename, export_type)
                        self.db.add_audit_log(update.effective_user.id, 'EXPORT_STATUS', f"Status bo'yicha eksport: {status}")
                    else:
                        await self.export_handler.send_message(update, context, f"❌ {status} statusidagi vazifalar topilmadi.", self.export_handler.create_back_button("export_menu"))
            elif data.startswith("export_worker_"):
                # Ishchi bo'yicha eksport
                user_id = int(data.split('_')[2])
                export_type = data.split('_')[3]
                tasks = self.export_handler.get_tasks_by_user(user_id)
                file_data = self.export_handler.create_xlsx_export(tasks)
                filename = f"ishchi_vazifalar_{user_id}_{update.effective_user.id}.xlsx"
                await self.export_handler.send_file(update, context, file_data, filename, export_type, task_count=len(tasks))
            
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
            elif data == "edit_reminder":
                await self.settings_handler.handle_edit_reminder(update, context)
            elif data.startswith("reminder_unit_"):
                await self.settings_handler.handle_reminder_unit_selection(update, context)
            elif data.startswith("timezone_"):
                await self.settings_handler.handle_timezone_selection(update, context)
            
            elif data == "disabled":
                # Disabled tugma - hech narsa qilmaydi
                await query.answer("⚠️ Bu funksiya hozircha mavjud emas!", show_alert=True)
            else:
                await query.answer("❌ Noma'lum buyruq!")
        
        except Exception as e:
            logger.error(f"Callback query xatoligi: {e}", exc_info=True)
            try:
                if query:
                    await query.answer("❌ Xatolik yuz berdi!")
            except Exception as answer_error:
                logger.error(f"Callback query answer xatosi: {answer_error}")
    
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
            elif state == 'waiting_start_photo':
                # Rasm kutilmoqda, boshqa narsa yuborilgan
                await update.message.reply_text("❌ Iltimos faqat kamera oldida tushgan rasmiz yuboring!")
            elif state == 'waiting_end_photo':
                # Rasm kutilmoqda, boshqa narsa yuborilgan
                await update.message.reply_text("❌ Iltimos faqat kamera oldida tushgan rasmiz yuboring!")
            elif state == 'search_by_date':
                # Sana bo'yicha qidirish
                try:
                    from datetime import datetime
                    date_str = update.message.text.strip()
                    search_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                    # Bu sanada yaratilgan vazifalarni qidirish
                    query = """
                        SELECT t.*, u.full_name as assigned_name 
                        FROM tasks t 
                        LEFT JOIN users u ON t.assigned_to = u.id 
                        WHERE DATE(t.created_at) = ?
                        ORDER BY t.created_at DESC
                    """
                    tasks = self.task_handler.db.execute_query(query, (search_date.strftime("%Y-%m-%d"),))
                    if tasks:
                        text = f"📅 <b>{date_str} sanasidagi vazifalar</b> ({len(tasks)} ta)\n\n"
                        for i, task in enumerate(tasks[:10], 1):
                            from utils import get_status_emoji, get_priority_emoji
                            status_emoji = get_status_emoji(task['status'])
                            priority_emoji = get_priority_emoji(task['priority'])
                            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
                            text += f"   👤 {task['assigned_name'] or 'Tayinlanmagan'}\n"
                            text += f"   {priority_emoji} {task['priority']}\n\n"
                        if len(tasks) > 10:
                            text += f"\n... va yana {len(tasks) - 10} ta vazifa"
                        reply_markup = self.task_handler.create_back_button("search_tasks")
                        await self.task_handler.send_message(update, context, text, reply_markup)
                    else:
                        await self.task_handler.send_message(update, context, f"❌ {date_str} sanasida vazifalar topilmadi.", self.task_handler.create_back_button("search_tasks"))
                    # Holatni tozalash
                    self.task_handler.user_states.pop(user['id'], None)
                except ValueError:
                    await self.task_handler.send_message(update, context, "❌ Noto'g'ri sana formati! Iltimos, DD.MM.YYYY formatida kiriting.\nMasalan: 01.01.2024")
                except Exception as e:
                    logger.error(f"Sana bo'yicha qidirishda xatolik: {e}")
                    await self.task_handler.send_message(update, context, "❌ Xatolik yuz berdi!", self.task_handler.create_back_button("search_tasks"))
                    self.task_handler.user_states.pop(user['id'], None)
        
        elif user['id'] in self.user_handler.user_states:
            state = self.user_handler.user_states[user['id']]
            
            if state in ['adding_admin', 'adding_worker']:
                await self.user_handler.handle_user_identifier(update, context)
        
        elif user['id'] in self.settings_handler.user_states:
            state = self.settings_handler.user_states[user['id']]
            
            # Holatlar ustuvorligi (eng yuqoridan pastga):
            # 1. Ogohlantirish qiymatini kiritish - birinchi tekshirish (eng yuqori ustuvorlik)
            if state == 'editing_reminder_value':
                await self.settings_handler.handle_reminder_value_input(update, context)
            # 2. Ish soati sozlamalari
            elif state == 'editing_work_start':
                await self.settings_handler.handle_work_start_input(update, context)
            elif state == 'editing_work_end':
                await self.settings_handler.handle_work_end_input(update, context)
            # 3. Boshqa sozlamalar
            elif state == 'editing_org_name':
                await self.settings_handler.handle_org_name_input(update, context)
            elif state == 'editing_penalty':
                await self.settings_handler.handle_penalty_input(update, context)
        
        else:
            # Oddiy xabar
            await update.message.reply_text(
                "🤖 Bot ishlamoqda. /start komandasini bosing."
            )
    
    async def handle_photo(self, update, context):
        """Rasm xabarlarini boshqarish"""
        user = self.start_handler.get_user(update)
        
        # Foydalanuvchi holatini tekshirish
        if user['id'] in self.task_handler.user_states:
            state = self.task_handler.user_states[user['id']]
            
            if state == 'waiting_start_photo':
                await self.task_handler.handle_start_work_photo(update, context)
            elif state == 'waiting_end_photo':
                await self.task_handler.handle_end_work_photo(update, context)
        else:
            # Agar rasm kutilmagan bo'lsa
            await update.message.reply_text("❌ Iltimos faqat kamera oldida tushgan rasmiz yuboring!")
    
    async def handle_contact(self, update, context):
        """Contact xabarlarini boshqarish"""
        user = self.start_handler.get_user(update)
        
        # Registratsiya holatini tekshirish
        if hasattr(self.start_handler, 'user_states') and user['id'] in self.start_handler.user_states:
            state = self.start_handler.user_states[user['id']]
            
            if state in ['waiting_phone', 'waiting_phone_text', 'waiting_phone_contact']:
                await self.start_handler.handle_phone_input(update, context)
    
    def start_bot(self):
        """Botni ishga tushirish"""
        logger.info("Bot ishga tushmoqda...")
        
        # Botni ishga tushirish (run_polling avtomatik initialize, start va polling qiladi)
        # run_polling() o'zi event loop yaratadi, shuning uchun asyncio.run() ishlatmaymiz
        try:
            self.application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
        except KeyboardInterrupt:
            logger.info("Bot foydalanuvchi tomonidan to'xtatildi")
        except Exception as e:
            error_str = str(e)
            # Conflict xatosi - boshqa bot instance ishlamoqda
            if "Conflict" in error_str or "terminated by other getUpdates" in error_str:
                logger.warning("⚠️ Boshqa bot instance ishlamoqda. Bu odatda vaqtincha xato.")
                logger.info("Bot avtomatik qayta urinadi. Agar muammo davom etsa, barcha bot instance'larni to'xtating.")
                # Bu xato odatda o'z-o'zidan hal bo'ladi, shuning uchun faqat log qilamiz
                return
            # InvalidToken xatosi - bot token noto'g'ri
            elif "Unauthorized" in error_str or "InvalidToken" in error_str:
                logger.error("❌ Bot token noto'g'ri yoki o'chirilgan!")
                logger.error("Iltimos, .env faylida BOT_TOKEN ni tekshiring va to'g'ri ekanligiga ishonch hosil qiling.")
                print("❌ Bot token noto'g'ri yoki o'chirilgan! .env faylida BOT_TOKEN ni tekshiring.")
                return
            else:
                logger.error(f"Bot xatosi: {e}", exc_info=True)
                raise
        finally:
            logger.info("Bot to'xtatildi")

def main():
    """Asosiy funksiya"""
    # Bot tokenini tekshirish
    if not BOT_TOKEN or len(BOT_TOKEN) < 10:
        logger.error("❌ BOT_TOKEN noto'g'ri yoki yo'q!")
        print("❌ BOT_TOKEN sozlanmagan yoki noto'g'ri! .env faylini yarating va BOT_TOKEN qo'shing.")
        return
    
    # Botni ishga tushirish
    try:
        bot = IshBot()
        bot.start_bot()
    except Exception as e:
        logger.error(f"Bot ishga tushirishda xatolik: {e}", exc_info=True)
        print(f"❌ Bot ishga tushirishda xatolik: {e}")

if __name__ == "__main__":
    main()

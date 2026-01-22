from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from handlers.resubmit_handler import ResubmitHandler
from handlers.tasks_notifications import TaskNotificationHandler
from config import UserRole
from utils import format_datetime, get_status_emoji, get_priority_emoji, calculate_time_remaining, get_uzbek_time, format_penalty_amount, mask_phone_number
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TaskHandler(BaseHandler):
    def __init__(self, db):
        super().__init__(db)
        self.user_states = {}
        self.resubmit_handler = ResubmitHandler(db)
        self.notification_handler = TaskNotificationHandler(db)
    
    async def handle_create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa yaratish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Foydalanuvchi holatini o'rnatish
        self.user_states[user['id']] = 'creating_task'
        
        text = """
📝 <b>Yangi vazifa yaratish</b>

Vazifa sarlavhasini yuboring:
        """
        
        reply_markup = self.create_back_button("main_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_task_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa sarlavhasini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'creating_task':
            return
        
        title = update.message.text
        self.user_states[user['id']] = 'task_description'
        self.user_states[f"{user['id']}_title"] = title
        
        text = f"""
📝 <b>Sarlavha:</b> {title}

Vazifa tavsifini yuboring yoki "O'tkazib yuborish" tugmasini bosing:
        """
        
        keyboard = [
            [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_description")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_task_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa tavsifini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'task_description':
            return
        
        description = update.message.text
        self.user_states[user['id']] = 'task_start_time'
        self.user_states[f"{user['id']}_description"] = description
        
        text = f"""
📝 <b>Sarlavha:</b> {self.user_states[f"{user['id']}_title"]}
📄 <b>Tavsif:</b> {description}

Boshlanish vaqtini yuboring (DD.MM.YYYY HH:MM formatida):
        """
        
        await self.send_message(update, context, text)
    
    async def handle_task_start_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa boshlanish vaqtini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'task_start_time':
            return
        
        try:
            start_time_str = update.message.text.strip()
            start_time = datetime.strptime(start_time_str, "%d.%m.%Y %H:%M")
            start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
            
            self.user_states[user['id']] = 'task_deadline'
            self.user_states[f"{user['id']}_start_time"] = start_time
            
            text = f"""
📝 <b>Sarlavha:</b> {self.user_states[f"{user['id']}_title"]}
📄 <b>Tavsif:</b> {self.user_states.get(f"{user['id']}_description", "Tavsif yo'q")}
📅 <b>Boshlanish:</b> {format_datetime(start_time)}

Deadline vaqtini yuboring (DD.MM.YYYY HH:MM formatida):
            """
            
            await self.send_message(update, context, text)
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Iltimos, DD.MM.YYYY HH:MM formatida yuboring.")
    
    async def handle_task_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa deadline'ini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'task_deadline':
            return
        
        try:
            deadline_str = update.message.text.strip()
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
            deadline = deadline.strftime("%Y-%m-%d %H:%M:%S")
            
            # Vazifa yaratish
            task_id = str(uuid.uuid4()).replace('-', '').upper()[:25]
            title = self.user_states[f"{user['id']}_title"]
            description = self.user_states.get(f"{user['id']}_description", "")
            start_time = self.user_states[f"{user['id']}_start_time"]
            
            # Ishchilarni olish
            workers = self.db.get_active_users()
            workers = [w for w in workers if w['role'] == 'WORKER']
            
            if not workers:
                await self.send_message(update, context, "❌ Hozircha ishchilar yo'q!")
                self.user_states.pop(user['id'], None)
                return
            
            text = f"""
📝 <b>Sarlavha:</b> {title}
📄 <b>Tavsif:</b> {description}
📅 <b>Boshlanish:</b> {format_datetime(start_time)}
⏰ <b>Deadline:</b> {format_datetime(deadline)}

Ustuvorlikni tanlang:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🔴 YUQORI", callback_data=f"priority_YUQORI_{task_id}"),
                    InlineKeyboardButton("🟡 ORTA", callback_data=f"priority_ORTA_{task_id}")
                ],
                [
                    InlineKeyboardButton("🟢 PAST", callback_data=f"priority_PAST_{task_id}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_message(update, context, text, reply_markup)
            
            # Vazifa ma'lumotlarini saqlash
            self.user_states[f"{user['id']}_task_id"] = task_id
            self.user_states[f"{user['id']}_deadline"] = deadline
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Iltimos, DD.MM.YYYY HH:MM formatida yuboring.")
    
    async def handle_task_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifa ustuvorligini tanlash"""
        user = self.get_user(update)
        data = update.callback_query.data.split('_')
        priority = data[1]
        task_id = data[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Ustuvorlikni saqlash
        self.user_states[f"{user['id']}_priority"] = priority
        
        # Vazifa ma'lumotlarini olish
        title = self.user_states[f"{user['id']}_title"]
        description = self.user_states.get(f"{user['id']}_description", "")
        start_time = self.user_states[f"{user['id']}_start_time"]
        deadline = self.user_states[f"{user['id']}_deadline"]
        
        # Ishchilarni olish
        workers = self.db.get_active_users()
        workers = [w for w in workers if w['role'] == 'WORKER']
        
        priority_emoji = "🔴" if priority == "YUQORI" else "🟡" if priority == "ORTA" else "🟢"
        
        text = f"""
📝 <b>Sarlavha:</b> {title}
📄 <b>Tavsif:</b> {description}
📅 <b>Boshlanish:</b> {format_datetime(start_time)}
⏰ <b>Deadline:</b> {format_datetime(deadline)}
{priority_emoji} <b>Ustuvorlik:</b> {priority}

Ishchini tanlang:
        """
        
        keyboard = []
        for worker in workers:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {worker['full_name']}", 
                    callback_data=f"assign_{worker['id']}_{task_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_task_assign(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchini tayinlash"""
        user = self.get_user(update)
        data = update.callback_query.data.split('_')
        worker_id = int(data[1])
        task_id = data[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        try:
            # Vazifa ma'lumotlarini olish
            title = self.user_states[f"{user['id']}_title"]
            description = self.user_states.get(f"{user['id']}_description", "")
            start_time = self.user_states[f"{user['id']}_start_time"]
            deadline = self.user_states[f"{user['id']}_deadline"]
            priority = self.user_states.get(f"{user['id']}_priority", "ORTA")
            
            # Vazifani yaratish
            self.db.create_task(
                task_id=task_id,
                title=title,
                description=description,
                created_by=user['id'],
                assigned_to=worker_id,
                start_at=start_time,
                deadline=deadline,
                priority=priority
            )
            
            # Ishchini olish
            worker = self.db.get_user_by_id(worker_id)
            assignee_name = worker['full_name'] if worker else "Noma'lum"
            assignee_telegram_id = worker['telegram_id'] if worker else None
            
            # Audit log
            self.db.add_audit_log(
                user['id'], 
                'TASK_CREATED', 
                f"Yangi vazifa yaratildi: {title} - {assignee_name}"
            )
            
            # Foydalanuvchi holatini tozalash
            self.user_states.pop(user['id'], None)
            self.user_states.pop(f"{user['id']}_title", None)
            self.user_states.pop(f"{user['id']}_description", None)
            self.user_states.pop(f"{user['id']}_start_time", None)
            self.user_states.pop(f"{user['id']}_deadline", None)
            self.user_states.pop(f"{user['id']}_priority", None)
            self.user_states.pop(f"{user['id']}_task_id", None)
            
            text = f"""
✅ <b>Vazifa yaratildi!</b>

📝 <b>Sarlavha:</b> {title}
👷 <b>Ishchi:</b> {assignee_name}
⏰ <b>Deadline:</b> {format_datetime(deadline)}
            """
            
            reply_markup = self.create_main_menu(user['role'])
            await self.send_message(update, context, text, reply_markup)
            
            # Ishchiga xabar yuborish (telegram_id bo'yicha)
            if assignee_telegram_id:
                logger.info(f"Vazifa biriktirilgan ishchiga xabar yuborilmoqda: {assignee_name} (Telegram ID: {assignee_telegram_id})")
                try:
                    await self.notify_worker_task_assigned(assignee_telegram_id, task_id, title, deadline, context)
                except Exception as notify_error:
                    logger.error(f"Xabar yuborishda xatolik: {notify_error}", exc_info=True)
            else:
                logger.error(f"⚠️ Ishchining telegram_id topilmadi: {worker_id} (Ishchi: {assignee_name})")
            
        except Exception as e:
            logger.error(f"Vazifa yaratishda xatolik: {e}")
            await self.send_message(update, context, "❌ Vazifa yaratishda xatolik yuz berdi!")
    
    async def notify_worker_task_assigned(self, worker_telegram_id: int, task_id: str, task_title: str, task_deadline: str, context: ContextTypes.DEFAULT_TYPE):
        """Ishchiga yangi vazifa tayinlanganini xabar qilish"""
        try:
            # Bot tekshiruvi
            if not context or not hasattr(context, 'bot') or not context.bot:
                logger.error("Context yoki bot None!")
                return
            
            worker = self.db.get_user_by_telegram_id(worker_telegram_id)
            if not worker:
                logger.error(f"Ishchi topilmadi: {worker_telegram_id}")
                return
            
            # Ishchi faol emas bo'lsa, xabar yubormaslik
            if not worker.get('is_active', True):
                logger.info(f"Ishchi faol emas, xabar yuborilmaydi: {worker['full_name']}")
                return

            notification_text = f"""
📝 <b>Yangi vazifa tayinlandi!</b>

📋 <b>Vazifa:</b> {task_title}
⏰ <b>Deadline:</b> {format_datetime(task_deadline)}
📅 <b>Tayinlangan vaqt:</b> {format_datetime(get_uzbek_time())}

Vazifani bajarishni boshlang!
            """
            
            keyboard = [
                [InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=worker_telegram_id,
                text=notification_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ Vazifa xabari yuborildi ishchiga: {worker['full_name']} (ID: {worker_telegram_id})")
            
        except Exception as e:
            logger.error(f"❌ Ishchiga xabar yuborishda xatolik: {e}", exc_info=True)
    
    async def handle_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifalar menyusi"""
        user = self.get_user(update)
        
        if user['role'] == UserRole.WORKER:
            text = """
📋 <b>Mening vazifalarim</b>

Vazifalaringizni ko'rish uchun quyidagi tugmalardan birini tanlang:
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 Faol vazifalar", callback_data="my_tasks")],
                [InlineKeyboardButton("✅ Bajarilgan ishlar", callback_data="completed_tasks")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_message(update, context, text, reply_markup)
            return
        
        # Admin va Super Admin uchun barcha vazifalar
        text = """
📋 <b>Vazifalar menyusi</b>

Vazifalarni boshqarish uchun quyidagi tugmalardan birini tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("📝 Mening vazifalarim", callback_data="my_tasks")],
            [InlineKeyboardButton("🔍 Barcha vazifalar", callback_data="all_tasks")],
            [InlineKeyboardButton("⏳ Tasdiqlash kerak", callback_data="pending_approval")],
            [InlineKeyboardButton("🔎 Qidiruv/Filtr", callback_data="search_tasks")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_search_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Qidiruv/Filtr menyusi"""
        
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        text = """
🔍 <b>Qidiruv va Filtr</b>

Qanday qidirish kerak?
        """
        
        keyboard = [
            [InlineKeyboardButton("👤 Ishlar bo'yicha qidirish", callback_data="search_by_worker")],
            [InlineKeyboardButton("📅 Sana bo'yicha qidirish", callback_data="search_by_date")],
            [InlineKeyboardButton("📊 Status bo'yicha qidirish", callback_data="search_by_status")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_pending_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tasdiqlash kerak bo'lgan vazifalar"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Tasdiqlash kerak bo'lgan vazifalarni olish
        query = """
            SELECT t.*, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.status = 'TASDIQLASH_KUTILMOQDA'
            ORDER BY t.created_at DESC
        """
        tasks = self.db.execute_query(query)
        
        if not tasks:
            text = "✅ Hozircha tasdiqlash kerak bo'lgan vazifalar yo'q."
            reply_markup = self.create_back_button("tasks_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"⏳ <b>Tasdiqlash kerak</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   👤 {task['assigned_name']}\n"
            text += f"   {priority_emoji} {task['priority']}\n"
            text += f"   📅 {format_datetime(task['deadline'])}\n\n"
        
        # Tugmalar
        keyboard = [
            [InlineKeyboardButton("🔙 Orqaga", callback_data="tasks_menu")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_all_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Barcha vazifalar"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Barcha vazifalarni olish
        query = """
            SELECT t.*, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            ORDER BY t.created_at DESC
        """
        tasks = self.db.execute_query(query)
        
        if not tasks:
            text = "📝 Hozircha vazifalar yo'q."
            reply_markup = self.create_back_button("tasks_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"📋 <b>Barcha vazifalar</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   👤 {task['assigned_name']}\n"
            text += f"   {priority_emoji} {task['priority']} | {status_emoji} {task['status']}\n"
            text += f"   📅 {format_datetime(task['deadline'])}\n\n"
        
        # Tugmalar
        keyboard = [
            [InlineKeyboardButton("🔙 Orqaga", callback_data="tasks_menu")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_worker_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchilar uchun vazifalar menyusi"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        text = """
📋 <b>Vazifalar menyusi</b>

Quyidagi bo'limlardan birini tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Faol vazifalar", callback_data="active_tasks")],
            [InlineKeyboardButton("✅ Bajarilgan ishlar", callback_data="completed_tasks")],
            [InlineKeyboardButton("❌ Muvaffaqiyatsiz", callback_data="failed_tasks")],
            [InlineKeyboardButton("⏳ Tasdiqlash kutilmoqda", callback_data="worker_pending_tasks")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_worker_pending_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchining tasdiqlash kutilayotgan vazifalari"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        # Tasdiqlash kutilayotgan vazifalar
        tasks = self.db.get_user_tasks_by_status(user['id'], ['TASDIQLASH_KUTILMOQDA'])
        
        if not tasks:
            text = "⏳ Hozircha tasdiqlash kutilayotgan vazifalar yo'q."
            reply_markup = self.create_back_button("worker_tasks_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"⏳ <b>Tasdiqlash kutilayotgan vazifalar</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   {priority_emoji} {task['priority']}\n"
            text += f"   📅 {format_datetime(task['deadline'])}\n\n"
        
        keyboard = []
        for task in tasks:
            keyboard.append([
                InlineKeyboardButton(
                    f"👁 {task['title'][:30]}...", 
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="worker_tasks_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_worker_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchining statistikasi"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        # Statistikani hisoblash
        all_tasks = self.db.get_user_tasks_by_status(user['id'], [])
        active_tasks = self.db.get_user_tasks_by_status(user['id'], ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA'])
        completed_tasks = self.db.get_user_tasks_by_status(user['id'], ['BAJARILDI'])
        failed_tasks = self.db.get_user_tasks_by_status(user['id'], ['RAD_ETILDI', 'MUDDATI_OTGAN'])
        pending_tasks = self.db.get_user_tasks_by_status(user['id'], ['TASDIQLASH_KUTILMOQDA'])
        
        # Jarima hisoblash
        query = """
            SELECT SUM(penalty_amount) as total_penalty, COUNT(*) as penalized_count
            FROM tasks
            WHERE assigned_to = ? AND is_penalized = TRUE
        """
        penalty_result = self.db.execute_query(query, (user['id'],))
        total_penalty = penalty_result[0]['total_penalty'] if penalty_result and penalty_result[0]['total_penalty'] else 0
        penalized_count = penalty_result[0]['penalized_count'] if penalty_result and penalty_result[0]['penalized_count'] else 0
        
        # Foiz hisoblash
        total_count = len(all_tasks)
        completed_percent = (len(completed_tasks) / total_count * 100) if total_count > 0 else 0
        
        text = f"""
📊 <b>Mening statistikam</b>

📈 <b>Umumiy ko'rsatkichlar:</b>
• 📋 Jami vazifalar: {total_count} ta
• 🔄 Faol vazifalar: {len(active_tasks)} ta
• ✅ Bajarilgan: {len(completed_tasks)} ta ({completed_percent:.1f}%)
• ❌ Muvaffaqiyatsiz: {len(failed_tasks)} ta
• ⏳ Tasdiqlash kutilmoqda: {len(pending_tasks)} ta

💰 <b>Jarima ma'lumotlari:</b>
• Jarima miqdori: {format_penalty_amount(total_penalty) if total_penalty > 0 else '0 UZS'}
• Jarima qilingan vazifalar: {penalized_count} ta

📅 <b>Oxirgi faollik:</b>
• Oxirgi vazifa: {format_datetime(all_tasks[0]['created_at']) if all_tasks else "Yo'q"}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yangilash", callback_data="worker_stats")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_worker_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchining ma'lumotlari"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        text = f"""
👤 <b>Mening ma'lumotlarim</b>

📝 <b>Ism familiya:</b> {user['full_name']}
🆔 <b>Telegram ID:</b> <code>{user['telegram_id']}</code>
📱 <b>Username:</b> @{user['username'] or "Yo'q"}
📞 <b>Telefon:</b> {mask_phone_number(user['phone']) if user['phone'] else 'Kiritilmagan'}
🎭 <b>Rol:</b> 👷 Ishchi
✅ <b>Holat:</b> {'Faol' if user['is_active'] else 'Nofaol'}

📅 <b>Registratsiya:</b> {format_datetime(user.get('created_at', '')) if user.get('created_at') else 'Nomalum'}
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="worker_stats")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_my_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mening vazifalarim menyusi"""
        user = self.get_user(update)
        
        if user['role'] == UserRole.WORKER:
            text = """
📋 <b>Mening vazifalarim</b>

Vazifalaringizni ko'rish uchun quyidagi tugmalardan birini tanlang:
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 Faol vazifalar", callback_data="active_tasks")],
                [InlineKeyboardButton("✅ Bajarilgan ishlar", callback_data="completed_tasks")],
                [InlineKeyboardButton("❌ Bajarilmagan vaqt o'tgan", callback_data="failed_tasks")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_message(update, context, text, reply_markup)
            return
        
        # Admin va Super Admin uchun barcha vazifalar
        text = f"📋 <b>Mening vazifalarim</b>\n\n"
        
        # Faqat faol vazifalar (BAJARILDI va RAD_ETILDI dan tashqari)
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA']
        tasks = self.db.get_user_tasks_by_status(user['id'], active_statuses)
        
        if not tasks:
            text += "🔄 Hozircha faol vazifalar yo'q."
            reply_markup = self.create_back_button("main_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text += f"🔄 <b>Faol vazifalar</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            time_remaining = calculate_time_remaining(task['deadline'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   {priority_emoji} {task['priority']} | {status_emoji} {task['status']}\n"
            text += f"   📅 {format_datetime(task['deadline'])} ({time_remaining})\n\n"
        
        # Tugmalar
        keyboard = []
        for i, task in enumerate(tasks, 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"👁 {task['title'][:30]}...", 
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_active_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Faol vazifalar"""
        user = self.get_user(update)
        
        # Faqat faol vazifalar (BAJARILDI va RAD_ETILDI dan tashqari)
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA']
        tasks = self.db.get_user_tasks_by_status(user['id'], active_statuses)
        
        if not tasks:
            text = "🔄 Hozircha faol vazifalar yo'q."
            reply_markup = self.create_back_button("my_tasks")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"🔄 <b>Faol vazifalar</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            time_remaining = calculate_time_remaining(task['deadline'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   {priority_emoji} {task['priority']} | {status_emoji} {task['status']}\n"
            text += f"   📅 {format_datetime(task['deadline'])} ({time_remaining})\n\n"
        
        # Tugmalar
        keyboard = []
        for i, task in enumerate(tasks, 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"👁 {task['title'][:30]}...", 
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="my_tasks")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_completed_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bajarilgan vazifalar"""
        user = self.get_user(update)
        
        # Faqat bajarilgan vazifalar (rad etilgan ishlar kiritilmaydi)
        completed_statuses = ['BAJARILDI']
        tasks = self.db.get_user_tasks_by_status(user['id'], completed_statuses)
        
        if not tasks:
            text = "✅ Hozircha bajarilgan vazifalar yo'q."
            reply_markup = self.create_back_button("tasks_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"✅ <b>Bajarilgan vazifalar</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            # Bajarilgan vaqt
            completed_time = ""
            if task['status'] == 'BAJARILDI' and task['completed_at']:
                completed_time = f"\n✅ Bajarilgan: {format_datetime(task['completed_at'])}"
            elif task['status'] == 'RAD_ETILDI' and task['completed_at']:
                completed_time = f"\n❌ Rad etilgan: {format_datetime(task['completed_at'])}"
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   {priority_emoji} {task['priority']}\n"
            text += f"   📅 {format_datetime(task['deadline'])}{completed_time}\n\n"
        
        # Tugmalar
        keyboard = []
        for i, task in enumerate(tasks, 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"👁 {task['title'][:30]}...", 
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="my_tasks")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_failed_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bajarilmagan vaqt o'tgan vazifalar"""
        user = self.get_user(update)
        
        # Muddati o'tgan va rad etilgan vazifalar
        failed_statuses = ['MUDDATI_OTGAN', 'RAD_ETILDI']
        tasks = self.db.get_user_tasks_by_status(user['id'], failed_statuses)
        
        if not tasks:
            text = "❌ Hozircha bajarilmagan vaqt o'tgan vazifalar yo'q."
            reply_markup = self.create_back_button("my_tasks")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"❌ <b>Bajarilmagan vaqt o'tgan</b> ({len(tasks)} ta)\n\n"
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            # Sabab
            reason = ""
            if task['status'] == 'MUDDATI_OTGAN':
                reason = "⏰ Muddati o'tgan"
            elif task['status'] == 'RAD_ETILDI':
                rejector_name = task.get('rejector_name', 'Nomalum')
                reason = f"🚫 {rejector_name} rad etgan"
            
            # Rad etilgan vaqt
            rejected_time = ""
            if task['status'] == 'RAD_ETILDI' and task.get('rejected_at'):
                rejected_time = f"\n❌ Rad etilgan: {format_datetime(task['rejected_at'])}"
            
            text += f"""
{i}. {status_emoji} <b>{task['title']}</b>
{priority_emoji} {task['priority']} | {reason}
📅 Deadline: {format_datetime(task['deadline'])}{rejected_time}
            """
        
        # Tugmalar
        keyboard = []
        for i, task in enumerate(tasks, 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"👁 {task['title'][:30]}...", 
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="my_tasks")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_view_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani ko'rish"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            return
        
        # Foydalanuvchi vazifaga ruxsati borligini tekshirish
        if user['role'] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifaga ruxsatingiz yo'q!")
            return
        
        status_emoji = get_status_emoji(task['status'])
        priority_emoji = get_priority_emoji(task['priority'])
        time_remaining = calculate_time_remaining(task['deadline'])
        
        text = f"""
{status_emoji} <b>{task['title']}</b>

📄 <b>Tavsif:</b> {task['description'] or 'Tavsif yoq'}
👤 <b>Ishchi:</b> {task.get('assigned_name', 'Nomalum')}
📅 <b>Boshlanish:</b> {format_datetime(task['start_at'])}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])} ({time_remaining})
{priority_emoji} <b>Ustuvorlik:</b> {task['priority']}
📊 <b>Status:</b> {task['status']}
        """
        
        # Bajarilgan vaqt
        if task['status'] == 'BAJARILDI' and task['completed_at']:
            text += f"\n✅ <b>Bajarilgan:</b> {format_datetime(task['completed_at'])}"
        elif task['status'] == 'RAD_ETILDI' and task.get('rejected_at'):
            text += f"\n❌ <b>Rad etilgan:</b> {format_datetime(task['rejected_at'])}"
        
        keyboard = []
        
        # Ishchi uchun tugmalar
        if user['role'] == UserRole.WORKER and task['assigned_to'] == user['id']:
            if task['status'] in ['REJALASHTIRILGAN', 'JARAYONDA']:
                keyboard.append([
                    InlineKeyboardButton("✅ Tugatdim", callback_data=f"complete_task_{task_id}"),
                    InlineKeyboardButton("❌ Ulgurmadim", callback_data=f"fail_task_{task_id}")
                ])
                keyboard.append([
                    InlineKeyboardButton("⏰ Deadline qo'shish so'rash", callback_data=f"request_extension_{task_id}")
                ])
            elif task['status'] == 'TASDIQLASH_KUTILMOQDA':
                # Qayta yuborish imkoniyatini tekshirish
                can_resubmit = self.db.can_resubmit_task(task_id)
                if can_resubmit:
                    resubmit_count = self.db.get_task_resubmit_count(task_id)
                    remaining_attempts = 3 - resubmit_count
                    keyboard.append([
                        InlineKeyboardButton(f"🔄 Qayta yuborish ({remaining_attempts} qoldi)", callback_data=f"resubmit_task_{task_id}")
                    ])
                else:
                    keyboard.append([
                        InlineKeyboardButton("⚠️ Qayta yuborish taqiqlangan", callback_data="disabled")
                    ])
        
        # Admin uchun tugmalar
        if user['role'] in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            if task['status'] == 'TASDIQLASH_KUTILMOQDA':
                keyboard.append([
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_task_{task_id}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_task_{task_id}")
                ])
            # Admin har doim qo'shimcha vaqt berishi mumkin
            keyboard.append([
                InlineKeyboardButton("⏰ Qo'shimcha vaqt bering", callback_data=f"extend_task_{task_id}")
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="my_tasks")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_complete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani tugatish"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifa sizga tegishli emas!")
            return
        
        if task['status'] not in ['REJALASHTIRILGAN', 'JARAYONDA']:
            await self.send_message(update, context, "❌ Vazifa tugatish uchun tayyor emas!")
            return
        
        # Statusni yangilash va tugatish vaqtini belgilash
        self.db.complete_task(task_id)
        
        # Audit log
        self.db.add_audit_log(user['id'], 'TASK_COMPLETED', f"Vazifa tugatildi: {task['title']}")
        
        # Admin'larga xabar yuborish
        await self.notification_handler.notify_admins_task_completed(task, user, context)
        
        text = f"""
✅ <b>Vazifa tugatildi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Tugatuvchi:</b> {user['full_name']}
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Admin'lar vazifani tasdiqlaydi.
        """
        
        reply_markup = self.create_back_button("my_tasks")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_approve_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani tasdiqlash"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['status'] != 'TASDIQLASH_KUTILMOQDA':
            await self.send_message(update, context, "❌ Vazifa tasdiqlash uchun tayyor emas!")
            return
        
        # Statusni yangilash va tasdiqlash vaqtini belgilash
        self.db.approve_task(task_id, user['id'])
        
        # Audit log
        self.db.add_audit_log(user['id'], 'TASK_APPROVED', f"Vazifa tasdiqlandi: {task['title']}")
        
        # Ishchiga xabar yuborish
        await self.notification_handler.notify_worker_task_approved(task, user, context)
        
        text = f"""
✅ <b>Vazifa tasdiqlandi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Tasdiqlovchi:</b> {user['full_name']}
        """
        
        reply_markup = self.create_back_button("tasks_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_reject_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani rad etish"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['status'] != 'TASDIQLASH_KUTILMOQDA':
            await self.send_message(update, context, "❌ Vazifa rad etish uchun tayyor emas!")
            return
        
        # Statusni yangilash
        self.db.update_task_status(task_id, 'RAD_ETILDI', rejected_by=user['id'])
        
        # Qayta yuborish sonini oshirish
        resubmit_count = self.db.increment_resubmit_count(task_id)
        
        # Agar 3 marta rad etilgan bo'lsa, shtraf qo'llash
        if resubmit_count >= 3:
            self.db.apply_penalty(task_id, 1000000)
            logger.info(f"Vazifa {task_id} uchun shtraf qo'llanildi: 1,000,000")
        
        # Audit log
        self.db.add_audit_log(user['id'], 'TASK_REJECTED', f"Vazifa rad etildi: {task['title']} (Qayta yuborish: {resubmit_count}/3)")
        
        # Ishchiga xabar yuborish
        await self.notification_handler.notify_worker_task_rejected(task, user, context, resubmit_count)
        
        text = f"""
❌ <b>Vazifa rad etildi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Rad etuvchi:</b> {user['full_name']}
        """
        
        reply_markup = self.create_back_button("tasks_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_search_by_worker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchi bo'yicha qidirish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Barcha ishchilarni olish
        workers = self.db.get_active_users()
        workers = [w for w in workers if w['role'] == 'WORKER']
        
        if not workers:
            text = "❌ Hozircha ishchilar yo'q."
            reply_markup = self.create_back_button("search_tasks")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = "👤 <b>Ishchini tanlang:</b>\n\n"
        
        keyboard = []
        for worker in workers:
            # Har bir ishchining vazifalar sonini olish
            worker_tasks = self.db.get_user_tasks_by_status(worker['id'], ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA'])
            task_count = len(worker_tasks)
            
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {worker['full_name']} ({task_count} ta vazifa)", 
                    callback_data=f"worker_tasks_{worker['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="search_tasks")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_search_by_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sana bo'yicha qidirish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        self.user_states[user['id']] = 'search_by_date'
        
        text = """
📅 <b>Sana bo'yicha qidirish</b>

Boshlanish sanasini yuboring (DD.MM.YYYY formatida):
Masalan: 01.01.2024
        """
        
        reply_markup = self.create_back_button("search_tasks")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_search_by_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status bo'yicha qidirish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        text = """
📊 <b>Status bo'yicha qidirish</b>

Statusni tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("📅 REJALASHTIRILGAN", callback_data="search_status_REJALASHTIRILGAN")],
            [InlineKeyboardButton("🔄 JARAYONDA", callback_data="search_status_JARAYONDA")],
            [InlineKeyboardButton("⏳ TASDIQLASH_KUTILMOQDA", callback_data="search_status_TASDIQLASH_KUTILMOQDA")],
            [InlineKeyboardButton("✅ BAJARILDI", callback_data="search_status_BAJARILDI")],
            [InlineKeyboardButton("❌ RAD_ETILDI", callback_data="search_status_RAD_ETILDI")],
            [InlineKeyboardButton("🚨 MUDDATI_OTGAN", callback_data="search_status_MUDDATI_OTGAN")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="search_tasks")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifalarni tahrirlash menyusi"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        text = """
✏️ <b>Vazifalarni tahrirlash</b>

Tahrirlash uchun vazifani tanlang:
        """
        
        # Faqat faol vazifalarni ko'rsatish
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA']
        query = """
            SELECT t.*, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.status IN ('REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA')
            ORDER BY t.created_at DESC
            LIMIT 10
        """
        tasks = self.db.execute_query(query)
        
        if not tasks:
            text += "\n❌ Tahrirlash uchun vazifalar yo'q."
            reply_markup = self.create_back_button("tasks_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        keyboard = []
        for task in tasks:
            status_emoji = get_status_emoji(task['status'])
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {task['title'][:40]}...", 
                    callback_data=f"edit_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="tasks_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_worker_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchining vazifalarini ko'rish"""
        user = self.get_user(update)
        worker_id = int(update.callback_query.data.split('_')[2])
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Ishchini olish
        worker = self.db.get_user_by_id(worker_id)
        if not worker:
            await self.send_message(update, context, "❌ Ishchi topilmadi!")
            return
        
        # Ishchining barcha vazifalarini olish
        query = """
            SELECT t.*, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.assigned_to = ?
            ORDER BY t.created_at DESC
        """
        tasks = self.db.execute_query(query, (worker_id,))
        
        text = f"👤 <b>{worker['full_name']} ning vazifalari</b>\n\n"
        
        if not tasks:
            text += "📝 Hozircha vazifalar yo'q."
            reply_markup = self.create_back_button("search_by_worker")
            await self.send_message(update, context, text, reply_markup)
            return
        
        for i, task in enumerate(tasks, 1):
            status_emoji = get_status_emoji(task['status'])
            priority_emoji = get_priority_emoji(task['priority'])
            
            text += f"{i}. {status_emoji} <b>{task['title']}</b>\n"
            text += f"   {priority_emoji} {task['priority']} | {status_emoji} {task['status']}\n"
            text += f"   📅 {format_datetime(task['deadline'])}\n\n"
        
        # Tugmalar
        keyboard = [
            [InlineKeyboardButton("🔙 Orqaga", callback_data="search_by_worker")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_worker_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchining vazifalarini tahrirlash"""
        user = self.get_user(update)
        worker_id = int(update.callback_query.data.split('_')[3])
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Ishchini olish
        worker = self.db.get_user_by_id(worker_id)
        if not worker:
            await self.send_message(update, context, "❌ Ishchi topilmadi!")
            return
        
        # Ishchining faol vazifalarini olish
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA']
        query = """
            SELECT t.*, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.assigned_to = ? AND t.status IN ('REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA')
            ORDER BY t.created_at DESC
        """
        tasks = self.db.execute_query(query, (worker_id,))
        
        text = f"✏️ <b>{worker['full_name']} ning vazifalarini tahrirlash</b>\n\n"
        
        if not tasks:
            text += "📝 Tahrirlash uchun faol vazifalar yo'q."
            reply_markup = self.create_back_button("edit_tasks")
            await self.send_message(update, context, text, reply_markup)
            return
        
        keyboard = []
        for task in tasks:
            status_emoji = get_status_emoji(task['status'])
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {task['title'][:40]}...", 
                    callback_data=f"edit_task_{task['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="edit_tasks")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani tahrirlash"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            return
        
        status_emoji = get_status_emoji(task['status'])
        priority_emoji = get_priority_emoji(task['priority'])
        
        text = f"""
✏️ <b>Vazifani tahrirlash</b>

{status_emoji} <b>{task['title']}</b>

📄 <b>Tavsif:</b> {task['description'] or 'Tavsif yoq'}
👤 <b>Ishchi:</b> {task.get('assigned_name', 'Nomalum')}
📅 <b>Boshlanish:</b> {format_datetime(task['start_at'])}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])}
{priority_emoji} <b>Ustuvorlik:</b> {task['priority']}
📊 <b>Status:</b> {task['status']}

Nimani o'zgartirmoqchisiz?
        """
        
        keyboard = [
            [InlineKeyboardButton("📝 Sarlavha", callback_data=f"edit_task_title_{task_id}")],
            [InlineKeyboardButton("📄 Tavsif", callback_data=f"edit_task_description_{task_id}")],
            [InlineKeyboardButton("⏰ Deadline", callback_data=f"edit_task_deadline_{task_id}")],
            [InlineKeyboardButton("📊 Status", callback_data=f"edit_task_status_{task_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="edit_tasks")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_start_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani boshlash"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifa sizga tegishli emas!")
            return
        
        if task['status'] != 'REJALASHTIRILGAN':
            await self.send_message(update, context, "❌ Vazifa boshlash uchun tayyor emas!")
            return
        
        # Statusni yangilash
        self.db.update_task_status(task_id, 'JARAYONDA')
        
        # Audit log
        self.db.add_audit_log(user['id'], 'TASK_STARTED', f"Vazifa boshladi: {task['title']}")
        
        text = f"""
▶️ <b>Vazifa boshladi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Boshlovchi:</b> {user['full_name']}
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Vazifani bajarishni davom eting!
        """
        
        reply_markup = self.create_back_button("my_tasks")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_fail_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vazifani bajarilmagan deb belgilash"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifa sizga tegishli emas!")
            return
        
        if task['status'] not in ['REJALASHTIRILGAN', 'JARAYONDA']:
            await self.send_message(update, context, "❌ Vazifa holati noto'g'ri!")
            return
        
        # Statusni yangilash
        self.db.update_task_status(task_id, 'MUDDATI_OTGAN')
        
        # Audit log
        self.db.add_audit_log(user['id'], 'TASK_FAILED', f"Vazifa bajarilmadi: {task['title']}")
        
        # Admin'larga xabar yuborish
        await self.notification_handler.notify_admins_task_failed(task, user, context)
        
        text = f"""
❌ <b>Vazifa bajarilmadi deb belgilandi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Ishchi:</b> {user['full_name']}
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Admin'lar xabardor qilindi.
        """
        
        reply_markup = self.create_back_button("my_tasks")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_request_extension(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Deadline uzaytirish so'rovi"""
        user = self.get_user(update)
        task_id = update.callback_query.data.split('_')[2]
        
        task = self.db.get_task_by_id(task_id)
        if not task or task['assigned_to'] != user['id']:
            await self.send_message(update, context, "❌ Bu vazifa sizga tegishli emas!")
            return
        
        if task['status'] not in ['REJALASHTIRILGAN', 'JARAYONDA']:
            await self.send_message(update, context, "❌ Vazifa holati noto'g'ri!")
            return
        
        # Foydalanuvchi holatini o'rnatish
        self.user_states[user['id']] = 'requesting_extension'
        self.user_states[f"{user['id']}_task_id"] = task_id
        
        text = f"""
⏰ <b>Deadline uzaytirish so'rovi</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Joriy deadline:</b> {format_datetime(task['deadline'])}

Sababini yuboring:
        """
        
        reply_markup = self.create_back_button(f"view_task_{task_id}")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_extension_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Deadline uzaytirish sababini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) != 'requesting_extension':
            return
        
        reason = update.message.text
        task_id = self.user_states[f"{user['id']}_task_id"]
        
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            self.user_states.pop(user['id'], None)
            self.user_states.pop(f"{user['id']}_task_id", None)
            return
        
        # Admin'larga xabar yuborish
        await self.notification_handler.notify_admins_extension_request(task, user, reason, context)
        
        # Foydalanuvchi holatini tozalash
        self.user_states.pop(user['id'], None)
        self.user_states.pop(f"{user['id']}_task_id", None)
        
        text = f"""
✅ <b>So'rov yuborildi!</b>

📝 <b>Vazifa:</b> {task['title']}
📄 <b>Sabab:</b> {reason}

Admin'lar sizning so'rovingizni ko'rib chiqadi.
        """
        
        reply_markup = self.create_back_button("my_tasks")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_approve_extension(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Deadline uzaytirishni qabul qilish"""
        user = self.get_user(update)
        data = update.callback_query.data.split('_')
        task_id = data[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Vazifani olish
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            return
        
        # Foydalanuvchi holatini o'rnatish
        self.user_states[f"{user['id']}_approve_extension"] = task_id
        self.user_states[user['id']] = f'approve_extension_{task_id}'
        
        text = f"""
✅ <b>Deadline uzaytirish qabul qilindi</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Joriy deadline:</b> {format_datetime(task['deadline'])}

Yangi deadline vaqtini yuboring (DD.MM.YYYY HH:MM formatida):
        """
        
        await self.send_message(update, context, text)
    
    async def handle_extension_time_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin'dan uzaytirish vaqtini qabul qilish"""
        user = self.get_user(update)
        
        if f"{user['id']}_approve_extension" not in self.user_states:
            return
        
        try:
            new_deadline_str = update.message.text.strip()
            new_deadline = datetime.strptime(new_deadline_str, "%d.%m.%Y %H:%M")
            new_deadline = new_deadline.strftime("%Y-%m-%d %H:%M:%S")
            
            task_id = self.user_states[f"{user['id']}_approve_extension"]
            self.user_states[f"{user['id']}_new_deadline"] = new_deadline
            self.user_states[user['id']] = f'new_deadline_{task_id}'
            
            text = f"""
✅ <b>Deadline vaqti qabul qilindi</b>

📅 <b>Yangi deadline:</b> {format_datetime(new_deadline)}

Iltimos, uzaytirish sababini yozing (izoh):
            """
            
            await self.send_message(update, context, text)
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Iltimos, DD.MM.YYYY HH:MM formatida yuboring.")
    
    async def handle_extension_comment_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin'dan uzaytirish izohini qabul qilish"""
        user = self.get_user(update)
        
        if f"{user['id']}_new_deadline" not in self.user_states:
            return
        
        try:
            comment = update.message.text.strip()
            task_id = self.user_states[f"{user['id']}_approve_extension"]
            new_deadline = self.user_states[f"{user['id']}_new_deadline"]
            
            # Vazifani olish
            task = self.db.get_task_by_id(task_id)
            if not task:
                await self.send_message(update, context, "❌ Vazifa topilmadi!")
                return
            
            # Deadline'ni yangilash
            old_deadline = task['deadline']
            self.db.update_task_deadline(task_id, new_deadline)
            
            # Deadline uzaytirish tarixini saqlash
            from datetime import datetime
            old_dt = datetime.strptime(old_deadline, "%Y-%m-%d %H:%M:%S")
            new_dt = datetime.strptime(new_deadline, "%Y-%m-%d %H:%M:%S")
            extension_hours = int((new_dt - old_dt).total_seconds() / 3600)
            
            self.db.add_deadline_extension(
                task_id=task_id,
                extended_by=user['id'],
                old_deadline=old_deadline,
                new_deadline=new_deadline,
                extension_hours=extension_hours,
                reason=comment
            )
            
            # Ishchini olish
            worker = self.db.get_user_by_id(task['assigned_to'])
            if worker:
                # Ishchiga xabar yuborish
                notification_text = f"""
✅ <b>Deadline uzaytirish qabul qilindi!</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Eski deadline:</b> {format_datetime(old_deadline)}
📅 <b>Yangi deadline:</b> {format_datetime(new_deadline)}
👤 <b>Qabul qiluvchi:</b> {user['full_name']}
💬 <b>Izoh:</b> {comment}

Vazifangiz uchun qo'shimcha vaqt berildi. Yangi deadline'ga rioya qiling!
                """
                
                keyboard = [
                    [InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=worker['telegram_id'],
                    text=notification_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                
                logger.info(f"Deadline uzaytirish qabul qilindi: {task['title']} - {worker['full_name']}")
            
            # Audit log
            self.db.add_audit_log(
                user['id'], 
                'EXTENSION_APPROVED', 
                f"Deadline uzaytirish qabul qilindi: {task['title']} - {format_datetime(new_deadline)} - {comment}"
            )
            
            # Foydalanuvchi holatini tozalash
            self.user_states.pop(user['id'], None)
            self.user_states.pop(f"{user['id']}_approve_extension", None)
            self.user_states.pop(f"{user['id']}_new_deadline", None)
            
            await self.send_message(update, context, f"""
✅ <b>Deadline uzaytirish muvaffaqiyatli qabul qilindi!</b>

📝 <b>Vazifa:</b> {task['title']}
📅 <b>Yangi deadline:</b> {format_datetime(new_deadline)}
💬 <b>Izoh:</b> {comment}

Ishchiga xabar yuborildi.
            """)
            
        except Exception as e:
            logger.error(f"Deadline uzaytirish qabul qilishda xatolik: {e}")
            await self.send_message(update, context, "❌ Xatolik yuz berdi!")
    
    async def handle_reject_extension(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Deadline uzaytirishni rad etish"""
        user = self.get_user(update)
        data = update.callback_query.data.split('_')
        task_id = data[2]
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat adminlar uchun!")
            return
        
        # Vazifani olish
        task = self.db.get_task_by_id(task_id)
        if not task:
            await self.send_message(update, context, "❌ Vazifa topilmadi!")
            return
        
        # Foydalanuvchi holatini o'rnatish
        self.user_states[f"{user['id']}_reject_extension"] = task_id
        self.user_states[user['id']] = f'reject_extension_{task_id}'
        
        text = f"""
❌ <b>Deadline uzaytirish rad etiladi</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])}

Rad etish sababini yozing:
        """
        
        await self.send_message(update, context, text)
    
    async def handle_rejection_reason_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin'dan rad etish sababini qabul qilish"""
        user = self.get_user(update)
        
        if f"{user['id']}_reject_extension" not in self.user_states:
            return
        
        try:
            reason = update.message.text.strip()
            task_id = self.user_states[f"{user['id']}_reject_extension"]
            
            # Vazifani olish
            task = self.db.get_task_by_id(task_id)
            if not task:
                await self.send_message(update, context, "❌ Vazifa topilmadi!")
                return
            
            # Ishchini olish
            worker = self.db.get_user_by_id(task['assigned_to'])
            if worker:
                # Ishchiga xabar yuborish
                notification_text = f"""
❌ <b>Deadline uzaytirish rad etildi</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])}
👤 <b>Rad etuvchi:</b> {user['full_name']}
💬 <b>Sabab:</b> {reason}

Deadline o'zgartirilmadi. Vazifani belgilangan vaqtda yakunlang!
                """
                
                keyboard = [
                    [InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=worker['telegram_id'],
                    text=notification_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                
                logger.info(f"Deadline uzaytirish rad etildi: {task['title']} - {worker['full_name']}")
            
            # Audit log
            self.db.add_audit_log(
                user['id'], 
                'EXTENSION_REJECTED', 
                f"Deadline uzaytirish rad etildi: {task['title']} - {reason}"
            )
            
            # Foydalanuvchi holatini tozalash
            self.user_states.pop(user['id'], None)
            self.user_states.pop(f"{user['id']}_reject_extension", None)
            
            await self.send_message(update, context, f"""
❌ <b>Deadline uzaytirish rad etildi!</b>

📝 <b>Vazifa:</b> {task['title']}
💬 <b>Sabab:</b> {reason}

Ishchiga xabar yuborildi.
            """)
            
        except Exception as e:
            logger.error(f"Deadline uzaytirish rad etishda xatolik: {e}")
            await self.send_message(update, context, "❌ Xatolik yuz berdi!")
    
    async def handle_start_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish boshlash - ish soati ma'lumotlari"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        # Tashkilot sozlamalarini olish
        org_settings = self.db.get_org_settings()
        if not org_settings:
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        work_start_hour = org_settings.get('work_hours_start', 9)
        work_end_hour = org_settings.get('work_hours_end', 18)
        
        # Hozirgi vaqt
        now = get_uzbek_time()
        work_start_time = now.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
        work_end_time = now.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)
        
        # Ish soati ma'lumotlari
        work_start_str = f"{work_start_hour:02d}:00"
        work_end_str = f"{work_end_hour:02d}:00"
        
        # Vaqtni tekshirish va real vaqtni hisoblash
        if now < work_start_time:
            # Ish soati boshlanmagan
            time_until_start = work_start_time - now
            hours = int(time_until_start.total_seconds() / 3600)
            minutes = int((time_until_start.total_seconds() % 3600) / 60)
            time_text = f"⏳ Ish vaqtingiz {work_start_str} da boshlanadi"
            if hours > 0:
                time_text += f" ({hours} soat {minutes} daqiqa qoldi)"
            else:
                time_text += f" ({minutes} daqiqa qoldi)"
        elif now >= work_start_time and now < work_end_time:
            # Ish soati boshlangan - real vaqtni hisoblash
            time_elapsed = now - work_start_time
            hours_elapsed = int(time_elapsed.total_seconds() / 3600)
            minutes_elapsed = int((time_elapsed.total_seconds() % 3600) / 60)
            
            # Qolgan vaqtni hisoblash
            time_remaining = work_end_time - now
            hours_remaining = int(time_remaining.total_seconds() / 3600)
            minutes_remaining = int((time_remaining.total_seconds() % 3600) / 60)
            
            time_text = f"✅ Ish vaqtingiz {work_start_str} da boshlangan"
            if hours_elapsed > 0:
                time_text += f"\n⏱️ Ish vaqti: {hours_elapsed} soat {minutes_elapsed} daqiqa o'tdi"
            else:
                time_text += f"\n⏱️ Ish vaqti: {minutes_elapsed} daqiqa o'tdi"
            
            if hours_remaining > 0:
                time_text += f"\n⏳ Qolgan vaqt: {hours_remaining} soat {minutes_remaining} daqiqa"
            else:
                time_text += f"\n⏳ Qolgan vaqt: {minutes_remaining} daqiqa"
        else:
            # Ish soati tugagan - real vaqtni hisoblash
            time_elapsed = work_end_time - work_start_time
            hours_elapsed = int(time_elapsed.total_seconds() / 3600)
            minutes_elapsed = int((time_elapsed.total_seconds() % 3600) / 60)
            
            time_text = f"⏰ Ish vaqtingiz {work_start_str} da boshlangan va {work_end_str} da tugagan"
            time_text += f"\n⏱️ Umumiy ish vaqti: {hours_elapsed} soat {minutes_elapsed} daqiqa"
        
        text = f"""
▶️ <b>Ish vaqtim boshlandi</b>

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}

{time_text}

📸 <b>Iltimos kamera tagiga borib rasm tushub yuboring!</b>
        """
        
        # Foydalanuvchi holatini o'rnatish - rasm kutish
        self.user_states[user['id']] = 'waiting_start_photo'
        
        reply_markup = self.create_back_button("main_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_end_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish tugatish - ish soati ma'lumotlari"""
        user = self.get_user(update)
        
        if user['role'] != UserRole.WORKER:
            await self.send_message(update, context, "❌ Bu funksiya faqat ishchilar uchun!")
            return
        
        # Tashkilot sozlamalarini olish
        org_settings = self.db.get_org_settings()
        if not org_settings:
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        work_start_hour = org_settings.get('work_hours_start', 9)
        work_end_hour = org_settings.get('work_hours_end', 18)
        
        # Hozirgi vaqt
        now = get_uzbek_time()
        work_end_time = now.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)
        
        # Ish soati ma'lumotlari
        work_start_str = f"{work_start_hour:02d}:00"
        work_end_str = f"{work_end_hour:02d}:00"
        
        # Vaqtni tekshirish va real vaqtni hisoblash
        work_start_time = now.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
        
        if now < work_end_time:
            # Ish soati tugamagan
            # O'tgan vaqtni hisoblash
            if now >= work_start_time:
                time_elapsed = now - work_start_time
                hours_elapsed = int(time_elapsed.total_seconds() / 3600)
                minutes_elapsed = int((time_elapsed.total_seconds() % 3600) / 60)
            else:
                hours_elapsed = 0
                minutes_elapsed = 0
            
            # Qolgan vaqtni hisoblash
            time_until_end = work_end_time - now
            hours_remaining = int(time_until_end.total_seconds() / 3600)
            minutes_remaining = int((time_until_end.total_seconds() % 3600) / 60)
            
            time_text = f"⏳ Ish vaqtingiz {work_end_str} da tugaydi"
            if hours_remaining > 0:
                time_text += f" ({hours_remaining} soat {minutes_remaining} daqiqa qoldi)"
            else:
                time_text += f" ({minutes_remaining} daqiqa qoldi)"
            
            if now >= work_start_time:
                if hours_elapsed > 0:
                    time_text += f"\n⏱️ Ish vaqti: {hours_elapsed} soat {minutes_elapsed} daqiqa o'tdi"
                else:
                    time_text += f"\n⏱️ Ish vaqti: {minutes_elapsed} daqiqa o'tdi"
        else:
            # Ish soati tugagan - real vaqtni hisoblash
            time_elapsed = work_end_time - work_start_time
            hours_elapsed = int(time_elapsed.total_seconds() / 3600)
            minutes_elapsed = int((time_elapsed.total_seconds() % 3600) / 60)
            
            time_text = f"✅ Ish vaqtingiz {work_end_str} da tugagan"
            time_text += f"\n⏱️ Umumiy ish vaqti: {hours_elapsed} soat {minutes_elapsed} daqiqa"
        
        text = f"""
✅ <b>Ish vaqtim tugatdi</b>

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}

{time_text}

📸 <b>Iltimos kamera tagiga borib rasm tushub yuboring!</b>
        """
        
        # Foydalanuvchi holatini o'rnatish - rasm kutish
        self.user_states[user['id']] = 'waiting_end_photo'
        
        reply_markup = self.create_back_button("main_menu")
        await self.send_message(update, context, text, reply_markup)
    
    
    async def handle_start_work_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish boshlash uchun rasm qabul qilish va kanalga yuborish"""
        user = self.get_user(update)
        
        # Rasm fayl ID sini olish
        photo = update.message.photo
        if not photo:
            await update.message.reply_text("❌ Iltimos faqat kamera oldida tushgan rasmiz yuboring!")
            return
        
        # Eng katta rasmni olish
        photo_file = photo[-1]
        file_id = photo_file.file_id
        
        # Tashkilot sozlamalarini olish
        org_settings = self.db.get_org_settings()
        if not org_settings:
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        work_start_hour = org_settings.get('work_hours_start', 9)
        work_end_hour = org_settings.get('work_hours_end', 18)
        work_start_str = f"{work_start_hour:02d}:00"
        work_end_str = f"{work_end_hour:02d}:00"
        
        # Hozirgi vaqt
        now = get_uzbek_time()
        current_time = format_datetime(now)
        
        # Audit log
        self.db.add_audit_log(user['id'], 'WORK_STARTED', f"Ish boshladi: {user['full_name']}")
        
        # Kanalga yuborish uchun matn
        from config import WORK_START_CHANNEL_ID
        if WORK_START_CHANNEL_ID:
            caption = f"""
▶️ <b>ISH BOSHLANDI</b>

👤 <b>Ishchi:</b> {user['full_name']}
📱 <b>Telefon:</b> {user.get('phone', 'Kiritilmagan')}
🆔 <b>ID:</b> {user['telegram_id']}

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}
📅 <b>Ish boshlangan vaqt:</b> {current_time}
            """
            
            try:
                await context.bot.send_photo(
                    chat_id=WORK_START_CHANNEL_ID,
                    photo=file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Kanalga rasm yuborishda xatolik: {e}")
        
        # Foydalanuvchi holatini tozalash
        self.user_states.pop(user['id'], None)
        
        # Foydalanuvchiga javob
        text = f"""
✅ <b>Rasm qabul qilindi va kanalga yuborildi!</b>

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}
📅 <b>Vaqt:</b> {current_time}

Ishingiz muvaffaqiyatli boshlandi!
        """
        
        reply_markup = self.create_back_button("main_menu")
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def handle_end_work_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ish tugatish uchun rasm qabul qilish va kanalga yuborish"""
        user = self.get_user(update)
        
        # Rasm fayl ID sini olish
        photo = update.message.photo
        if not photo:
            await update.message.reply_text("❌ Iltimos faqat kamera oldida tushgan rasmiz yuboring!")
            return
        
        # Eng katta rasmni olish
        photo_file = photo[-1]
        file_id = photo_file.file_id
        
        # Tashkilot sozlamalarini olish
        org_settings = self.db.get_org_settings()
        if not org_settings:
            self.db.create_org_settings("Yangi Tashkilot")
            org_settings = self.db.get_org_settings()
        
        work_start_hour = org_settings.get('work_hours_start', 9)
        work_end_hour = org_settings.get('work_hours_end', 18)
        work_start_str = f"{work_start_hour:02d}:00"
        work_end_str = f"{work_end_hour:02d}:00"
        
        # Hozirgi vaqt
        now = get_uzbek_time()
        current_time = format_datetime(now)
        
        # Audit log
        self.db.add_audit_log(user['id'], 'WORK_ENDED', f"Ish tugadi: {user['full_name']}")
        
        # Kanalga yuborish uchun matn
        from config import WORK_END_CHANNEL_ID
        if WORK_END_CHANNEL_ID:
            caption = f"""
✅ <b>ISH TUGATDI</b>

👤 <b>Ishchi:</b> {user['full_name']}
📱 <b>Telefon:</b> {user.get('phone', 'Kiritilmagan')}
🆔 <b>ID:</b> {user['telegram_id']}

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}
📅 <b>Ish tugatilgan vaqt:</b> {current_time}
            """
            
            try:
                await context.bot.send_photo(
                    chat_id=WORK_END_CHANNEL_ID,
                    photo=file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Kanalga rasm yuborishda xatolik: {e}")
        
        # Foydalanuvchi holatini tozalash
        self.user_states.pop(user['id'], None)
        
        # Foydalanuvchiga javob
        text = f"""
✅ <b>Rasm qabul qilindi va kanalga yuborildi!</b>

🕘 <b>Ish soati:</b> {work_start_str} - {work_end_str}
📅 <b>Vaqt:</b> {current_time}

Ishingiz muvaffaqiyatli yakunlandi!
        """
        
        reply_markup = self.create_back_button("main_menu")
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
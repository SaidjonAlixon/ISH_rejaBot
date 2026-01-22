from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from handlers.resubmit_handler import ResubmitHandler
from handlers.tasks_notifications import TaskNotificationHandler
from config import UserRole
from utils import format_datetime, get_status_emoji, get_priority_emoji, calculate_time_remaining, get_uzbek_time
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TaskHandler(BaseHandler):
    def __init__(self, db):
        super().__init__(db)
        self.user_states = {}
        self.resubmit_handler = ResubmitHandler(db)
        self.notification_handler = TaskNotificationHandler(db, None)
    
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
            
            # Vazifa ma'lumotlarini saqlash
            self.user_states[f"{user['id']}_task_id"] = task_id
            self.user_states[f"{user['id']}_deadline"] = deadline
            
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Iltimos, DD.MM.YYYY HH:MM formatida yuboring.")
    
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
            
            # Vazifani yaratish
            self.db.create_task(
                task_id=task_id,
                title=title,
                description=description,
                created_by=user['id'],
                assigned_to=worker_id,
                start_at=start_time,
                deadline=deadline,
                priority='ORTA'
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
                await self.notify_worker_task_assigned(assignee_telegram_id, task_id, title, deadline, context)
            else:
                logger.error(f"Ishchining telegram_id topilmadi: {worker_id}")
            
        except Exception as e:
            logger.error(f"Vazifa yaratishda xatolik: {e}")
            await self.send_message(update, context, "❌ Vazifa yaratishda xatolik yuz berdi!")
    
    async def notify_worker_task_assigned(self, worker_telegram_id: int, task_id: str, task_title: str, task_deadline: str, context: ContextTypes.DEFAULT_TYPE):
        """Ishchiga yangi vazifa tayinlanganini xabar qilish"""
        try:
            worker = self.db.get_user_by_telegram_id(worker_telegram_id)
            if not worker:
                logger.error(f"Ishchi topilmadi: {worker_telegram_id}")
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
            
            logger.info(f"Vazifa xabari yuborildi ishchiga: {worker['full_name']}")
            
        except Exception as e:
            logger.error(f"Ishchiga xabar yuborishda xatolik: {e}")
    
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
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA', 'MUDDATI_OTGAN']
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
        active_statuses = ['REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA', 'MUDDATI_OTGAN']
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
                rejector_name = task.get('rejector_name', 'Noma\'lum')
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

📄 <b>Tavsif:</b> {task['description'] or 'Tavsif yo\'q'}
👤 <b>Ishchi:</b> {task.get('assigned_name', 'Noma\'lum')}
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
            if task['status'] == 'REJALASHTIRILGAN':
                keyboard.append([
                    InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_task_{task_id}")
                ])
            elif task['status'] == 'JARAYONDA':
                keyboard.append([
                    InlineKeyboardButton("✅ Tugatish", callback_data=f"complete_task_{task_id}")
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
        
        if task['status'] != 'JARAYONDA':
            await self.send_message(update, context, "❌ Vazifa tugatish uchun tayyor emas!")
            return
        
        # Statusni yangilash
        self.db.update_task_status(task_id, 'TASDIQLASH_KUTILMOQDA')
        
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
        
        # Statusni yangilash
        self.db.update_task_status(task_id, 'BAJARILDI', user['id'])
        
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
    
    async def handle_search_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE): 
 
                 " " " Q i d i r u v / F i l t r   m e n y u s i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " " " 
 
 @_   < b > Q i d i r u v   v a   F i l t r < / b > 
 
 
 
 Q a n d a y   q i d i r i s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ �  I s h l a r   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ w o r k e r " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ &   S a n a   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ d a t e " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ 	  S t a t u s   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ s t a t u s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " m a i n _ m e n u " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " T a h r i r l a s h   m e n y u s i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " " " 
 
 @_: �   < b > T a h r i r l a s h < / b > 
 
 
 
 N i m a n i   t a h r i r l a s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ �  I s h l a r n i   t a n l a s h " ,   c a l l b a c k _ d a t a = " s e l e c t _ w o r k e r _ t a s k s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " 2�   D e a d l i n e   u z a y t i r i s h " ,   c a l l b a c k _ d a t a = " e x t e n d _ d e a d l i n e " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ \  V a z i f a   t a h r i r l a s h " ,   c a l l b a c k _ d a t a = " e d i t _ t a s k _ d e t a i l s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " m a i n _ m e n u " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ s e a r c h _ b y _ w o r k e r ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h l a r   b o ' y i c h a   q i d i r i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   B a r c h a   i s h c h i l a r n i   o l i s h 
 
                 w o r k e r s   =   s e l f . d b . g e t _ a c t i v e _ u s e r s ( ) 
 
                 w o r k e r s   =   [ w   f o r   w   i n   w o r k e r s   i f   w [ ' r o l e ' ]   = =   ' W O R K E R ' ] 
 
                 
 
                 i f   n o t   w o r k e r s : 
 
                         t e x t   =   " 2\
  H o z i r c h a   i s h c h i l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e a r c h _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " @_ �  < b > I s h c h i n i   t a n l a n g : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   w o r k e r   i n   w o r k e r s : 
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_ �   { w o r k e r [ ' f u l l _ n a m e ' ] } " ,   
 
                                         c a l l b a c k _ d a t a = f " w o r k e r _ t a s k s _ { w o r k e r [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e a r c h _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " T a n l a n g a n   i s h c h i n i n g   v a z i f a l a r i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 w o r k e r _ i d   =   i n t ( u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i   o l i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( w o r k e r _ i d ) 
 
                 i f   n o t   w o r k e r : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  I s h c h i   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i n g   b a r c h a   v a z i f a l a r i n i   o l i s h 
 
                 t a s k s   =   s e l f . d b . g e t _ u s e r _ t a s k s ( w o r k e r _ i d ) 
 
                 
 
                 i f   n o t   t a s k s : 
 
                         t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n 2\
  H o z i r c h a   v a z i f a l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e a r c h _ b y _ w o r k e r " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n @_ 9   < b > V a z i f a l a r : < / b >   ( { l e n ( t a s k s ) }   t a ) \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   i ,   t a s k   i n   e n u m e r a t e ( t a s k s ,   1 ) : 
 
                         s t a t u s _ e m o j i   =   g e t _ s t a t u s _ e m o j i ( t a s k [ ' s t a t u s ' ] ) 
 
                         p r i o r i t y _ e m o j i   =   g e t _ p r i o r i t y _ e m o j i ( t a s k [ ' p r i o r i t y ' ] ) 
 
                         
 
                         t e x t   + =   f " { i } .   { s t a t u s _ e m o j i }   < b > { t a s k [ ' t i t l e ' ] } < / b > \ n " 
 
                         t e x t   + =   f "       { p r i o r i t y _ e m o j i }   { t a s k [ ' p r i o r i t y ' ] }   |   { s t a t u s _ e m o j i }   { t a s k [ ' s t a t u s ' ] } \ n " 
 
                         t e x t   + =   f "       @_ &   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } \ n \ n " 
 
                         
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_   { t a s k [ ' t i t l e ' ] [ : 3 0 ] } . . . " ,   
 
                                         c a l l b a c k _ d a t a = f " v i e w _ t a s k _ { t a s k [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ w o r k e r " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ s e l e c t _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h l a r n i   t a n l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   B a r c h a   i s h c h i l a r n i   o l i s h 
 
                 w o r k e r s   =   s e l f . d b . g e t _ a c t i v e _ u s e r s ( ) 
 
                 w o r k e r s   =   [ w   f o r   w   i n   w o r k e r s   i f   w [ ' r o l e ' ]   = =   ' W O R K E R ' ] 
 
                 
 
                 i f   n o t   w o r k e r s : 
 
                         t e x t   =   " 2\
  H o z i r c h a   i s h c h i l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " e d i t _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " @_ �  < b > I s h c h i n i   t a n l a n g : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   w o r k e r   i n   w o r k e r s : 
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_ �   { w o r k e r [ ' f u l l _ n a m e ' ] } " ,   
 
                                         c a l l b a c k _ d a t a = f " e d i t _ w o r k e r _ t a s k s _ { w o r k e r [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " e d i t _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h c h i n i n g   v a z i f a l a r i n i   t a h r i r l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 w o r k e r _ i d   =   i n t ( u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 3 ] ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i   o l i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( w o r k e r _ i d ) 
 
                 i f   n o t   w o r k e r : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  I s h c h i   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i n g   f a o l   v a z i f a l a r i n i   o l i s h 
 
                 a c t i v e _ s t a t u s e s   =   [ ' R E J A L A S H T I R I L G A N ' ,   ' J A R A Y O N D A ' ,   ' T A S D I Q L A S H _ K U T I L M O Q D A ' ,   ' M U D D A T I _ O T G A N ' ] 
 
                 t a s k s   =   s e l f . d b . g e t _ u s e r _ t a s k s _ b y _ s t a t u s ( w o r k e r _ i d ,   a c t i v e _ s t a t u s e s ) 
 
                 
 
                 i f   n o t   t a s k s : 
 
                         t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n 2\
  H o z i r c h a   f a o l   v a z i f a l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e l e c t _ w o r k e r _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n @_: �   < b > T a h r i r l a s h   m u m k i n   b o ' l g a n   v a z i f a l a r : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   i ,   t a s k   i n   e n u m e r a t e ( t a s k s ,   1 ) : 
 
                         s t a t u s _ e m o j i   =   g e t _ s t a t u s _ e m o j i ( t a s k [ ' s t a t u s ' ] ) 
 
                         p r i o r i t y _ e m o j i   =   g e t _ p r i o r i t y _ e m o j i ( t a s k [ ' p r i o r i t y ' ] ) 
 
                         
 
                         t e x t   + =   f " { i } .   { s t a t u s _ e m o j i }   < b > { t a s k [ ' t i t l e ' ] } < / b > \ n " 
 
                         t e x t   + =   f "       { p r i o r i t y _ e m o j i }   { t a s k [ ' p r i o r i t y ' ] }   |   { s t a t u s _ e m o j i }   { t a s k [ ' s t a t u s ' ] } \ n " 
 
                         t e x t   + =   f "       @_ &   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } \ n \ n " 
 
                         
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " 2Z?Q  { t a s k [ ' t i t l e ' ] [ : 2 5 ] } . . . " ,   
 
                                         c a l l b a c k _ d a t a = f " e d i t _ t a s k _ { t a s k [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e l e c t _ w o r k e r _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ t a s k ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " V a z i f a n i   t a h r i r l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 t a s k _ i d   =   u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " " " 
 
 @_: �   < b > V a z i f a n i   t a h r i r l a s h < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ �   < b > I s h c h i : < / b >   { t a s k . g e t ( ' a s s i g n e d _ n a m e ' ,   ' N o m a \ ' l u m ' ) } 
 
 @_ &   < b > D e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } 
 
 
 
 N i m a n i   t a h r i r l a s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " 2�   D e a d l i n e   u z a y t i r i s h " ,   c a l l b a c k _ d a t a = f " e x t e n d _ t a s k _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ \  S a r l a v h a   o ' z g a r t i r i s h " ,   c a l l b a c k _ d a t a = f " e d i t _ t i t l e _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_    T a v s i f   o ' z g a r t i r i s h " ,   c a l l b a c k _ d a t a = f " e d i t _ d e s c r i p t i o n _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = f " e d i t _ w o r k e r _ t a s k s _ { t a s k [ ' a s s i g n e d _ t o ' ] } " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e x t e n d _ t a s k ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " V a z i f a   d e a d l i n e ' i n i   u z a y t i r i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 t a s k _ i d   =   u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   F o y d a l a n u v c h i   h o l a t i n i   o ' r n a t i s h 
 
                 s e l f . u s e r _ s t a t e s [ u s e r [ ' i d ' ] ]   =   f ' e x t e n d i n g _ d e a d l i n e _ { t a s k _ i d } ' 
 
                 
 
                 t e x t   =   f " " " 
 
 2�   < b > D e a d l i n e   u z a y t i r i s h < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > J o r i y   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } 
 
 
 
 Q a n c h a   v a q t   q o ' s h i s h   k e r a k ? 
 
 
 
 1 ?Q2S  -   1   s o a t 
 
 2 ?Q2S  -   2   s o a t     
 
 3 ?Q2S  -   3   s o a t 
 
 6 ?Q2S  -   6   s o a t 
 
 1 ?Q2S2 ?Q2S  -   1 2   s o a t 
 
 1 ?Q2Sd   -   1   k u n 
 
 2 ?Q2Sd   -   2   k u n 
 
 3 ?Q2Sd   -   3   k u n 
 
 1 ?Q2Sw   -   1   h a f t a 
 
 
 
 Y o k i   a n i q   v a q t n i   y u b o r i n g   ( m a s a l a n :   2 0 2 4 - 1 2 - 3 1   1 8 : 0 0 ) 
 
                 " " " 
 
                 
 
                 r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( f " e d i t _ t a s k _ { t a s k _ i d } " ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ d e a d l i n e _ e x t e n s i o n ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " D e a d l i n e   u z a y t i r i s h n i   q a b u l   q i l i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . u s e r _ s t a t e s . g e t ( u s e r [ ' i d ' ] ,   ' ' ) . s t a r t s w i t h ( ' e x t e n d i n g _ d e a d l i n e _ ' ) : 
 
                         r e t u r n 
 
                 
 
                 t a s k _ i d   =   s e l f . u s e r _ s t a t e s [ u s e r [ ' i d ' ] ] . s p l i t ( ' _ ' ) [ 2 ] 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         s e l f . u s e r _ s t a t e s . p o p ( u s e r [ ' i d ' ] ,   N o n e ) 
 
                         r e t u r n 
 
                 
 
                 e x t e n s i o n _ t e x t   =   u p d a t e . m e s s a g e . t e x t . s t r i p ( ) 
 
                 n e w _ d e a d l i n e   =   N o n e 
 
                 e x t e n s i o n _ h o u r s   =   0 
 
                 
 
                 #   V a q t   u z a y t i r i s h n i   h i s o b l a s h 
 
                 i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   1 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 2 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 3 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   3 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 6 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   6 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2S2 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   1 2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   2 4 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 2 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   4 8 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 3 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   7 2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2Sw " : 
 
                         e x t e n s i o n _ h o u r s   =   1 6 8 
 
                 e l s e : 
 
                         #   A n i q   v a q t   k i r i t i l g a n 
 
                         t r y : 
 
                                 f r o m   d a t e t i m e   i m p o r t   d a t e t i m e 
 
                                 n e w _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( e x t e n s i o n _ t e x t ,   " % Y - % m - % d   % H : % M " ) 
 
                                 n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                         e x c e p t   V a l u e E r r o r : 
 
                                 t r y : 
 
                                         n e w _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( e x t e n s i o n _ t e x t ,   " % d . % m . % Y   % H : % M " ) 
 
                                         n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                                 e x c e p t   V a l u e E r r o r : 
 
                                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  N o t o ' g ' r i   f o r m a t !   I l t i m o s ,   q a y t a   u r i n i b   k o ' r i n g . " ) 
 
                                         r e t u r n 
 
                 
 
                 i f   n o t   n e w _ d e a d l i n e : 
 
                         #   S o a t   q o ' s h i s h 
 
                         f r o m   d a t e t i m e   i m p o r t   d a t e t i m e ,   t i m e d e l t a 
 
                         c u r r e n t _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( t a s k [ ' d e a d l i n e ' ] ,   " % Y - % m - % d   % H : % M : % S " ) 
 
                         n e w _ d e a d l i n e   =   c u r r e n t _ d e a d l i n e   +   t i m e d e l t a ( h o u r s = e x t e n s i o n _ h o u r s ) 
 
                         n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                 
 
                 #   D a t a b a s e ' d a   d e a d l i n e ' n i   y a n g i l a s h 
 
                 s e l f . d b . e x e c u t e _ u p d a t e ( 
 
                         " U P D A T E   t a s k s   S E T   d e a d l i n e   =   ? ,   u p d a t e d _ a t   =   C U R R E N T _ T I M E S T A M P   W H E R E   i d   =   ? " , 
 
                         ( n e w _ d e a d l i n e ,   t a s k _ i d ) 
 
                 ) 
 
                 
 
                 #   D e a d l i n e   e x t e n s i o n   t a r i x i n i   s a q l a s h 
 
                 s e l f . d b . a d d _ d e a d l i n e _ e x t e n s i o n ( 
 
                         t a s k _ i d = t a s k _ i d , 
 
                         e x t e n d e d _ b y = u s e r [ ' i d ' ] , 
 
                         o l d _ d e a d l i n e = t a s k [ ' d e a d l i n e ' ] , 
 
                         n e w _ d e a d l i n e = n e w _ d e a d l i n e , 
 
                         e x t e n s i o n _ h o u r s = e x t e n s i o n _ h o u r s , 
 
                         r e a s o n = f " A d m i n   t o m o n i d a n   u z a y t i r i l d i :   { u s e r [ ' f u l l _ n a m e ' ] } " 
 
                 ) 
 
                 
 
                 #   A u d i t   l o g 
 
                 s e l f . d b . a d d _ a u d i t _ l o g ( 
 
                         u s e r [ ' i d ' ] ,   
 
                         ' D E A D L I N E _ E X T E N D E D ' ,   
 
                         f " V a z i f a   d e a d l i n e   u z a y t i r i l d i :   { t a s k [ ' t i t l e ' ] }   -   { e x t e n s i o n _ h o u r s }   s o a t   q o ' s h i l d i " 
 
                 ) 
 
                 
 
                 #   I s h c h i g a   x a b a r   y u b o r i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( t a s k [ ' a s s i g n e d _ t o ' ] ) 
 
                 i f   w o r k e r : 
 
                         t r y : 
 
                                 n o t i f i c a t i o n _ t e x t   =   f " " " 
 
 2�   < b > D e a d l i n e   u z a y t i r i l d i ! < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > Y a n g i   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( n e w _ d e a d l i n e ) } 
 
 @_ �   < b > A d m i n : < / b >   { u s e r [ ' f u l l _ n a m e ' ] } 
 
 
 
 V a z i f a   m u d d a t i   u z a y t i r i l d i . 
 
                                 " " " 
 
                                 
 
                                 a w a i t   c o n t e x t . b o t . s e n d _ m e s s a g e ( 
 
                                         c h a t _ i d = w o r k e r [ ' t e l e g r a m _ i d ' ] , 
 
                                         t e x t = n o t i f i c a t i o n _ t e x t , 
 
                                         p a r s e _ m o d e = ' H T M L ' 
 
                                 ) 
 
                         e x c e p t   E x c e p t i o n   a s   e : 
 
                                 l o g g e r . e r r o r ( f " I s h c h i g a   x a b a r   y u b o r i s h d a   x a t o l i k :   { e } " ) 
 
                 
 
                 t e x t   =   f " " " 
 
 2Z&   < b > D e a d l i n e   u z a y t i r i l d i ! < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > Y a n g i   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( n e w _ d e a d l i n e ) } 
 
 2�   < b > Q o ' s h i l g a n   v a q t : < / b >   { e x t e n s i o n _ h o u r s }   s o a t 
 
 
 
 I s h c h i g a   x a b a r   y u b o r i l d i . 
 
                 " " " 
 
                 
 
                 s e l f . u s e r _ s t a t e s . p o p ( u s e r [ ' i d ' ] ,   N o n e ) 
 
                 r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( f " e d i t _ w o r k e r _ t a s k s _ { t a s k [ ' a s s i g n e d _ t o ' ] } " ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         a s y n c   d e f   h a n d l e _ s e a r c h _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " Q i d i r u v / F i l t r   m e n y u s i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " " " 
 
 @_   < b > Q i d i r u v   v a   F i l t r < / b > 
 
 
 
 Q a n d a y   q i d i r i s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ �  I s h l a r   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ w o r k e r " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ &   S a n a   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ d a t e " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ 	  S t a t u s   b o ' y i c h a   q i d i r i s h " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ s t a t u s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " m a i n _ m e n u " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " T a h r i r l a s h   m e n y u s i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " " " 
 
 @_: �   < b > T a h r i r l a s h < / b > 
 
 
 
 N i m a n i   t a h r i r l a s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ �  I s h l a r n i   t a n l a s h " ,   c a l l b a c k _ d a t a = " s e l e c t _ w o r k e r _ t a s k s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " 2�   D e a d l i n e   u z a y t i r i s h " ,   c a l l b a c k _ d a t a = " e x t e n d _ d e a d l i n e " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ \  V a z i f a   t a h r i r l a s h " ,   c a l l b a c k _ d a t a = " e d i t _ t a s k _ d e t a i l s " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " m a i n _ m e n u " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ s e a r c h _ b y _ w o r k e r ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h l a r   b o ' y i c h a   q i d i r i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   B a r c h a   i s h c h i l a r n i   o l i s h 
 
                 w o r k e r s   =   s e l f . d b . g e t _ a c t i v e _ u s e r s ( ) 
 
                 w o r k e r s   =   [ w   f o r   w   i n   w o r k e r s   i f   w [ ' r o l e ' ]   = =   ' W O R K E R ' ] 
 
                 
 
                 i f   n o t   w o r k e r s : 
 
                         t e x t   =   " 2\
  H o z i r c h a   i s h c h i l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e a r c h _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " @_ �  < b > I s h c h i n i   t a n l a n g : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   w o r k e r   i n   w o r k e r s : 
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_ �   { w o r k e r [ ' f u l l _ n a m e ' ] } " ,   
 
                                         c a l l b a c k _ d a t a = f " w o r k e r _ t a s k s _ { w o r k e r [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e a r c h _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " T a n l a n g a n   i s h c h i n i n g   v a z i f a l a r i " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 w o r k e r _ i d   =   i n t ( u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i   o l i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( w o r k e r _ i d ) 
 
                 i f   n o t   w o r k e r : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  I s h c h i   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i n g   b a r c h a   v a z i f a l a r i n i   o l i s h 
 
                 t a s k s   =   s e l f . d b . g e t _ u s e r _ t a s k s ( w o r k e r _ i d ) 
 
                 
 
                 i f   n o t   t a s k s : 
 
                         t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n 2\
  H o z i r c h a   v a z i f a l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e a r c h _ b y _ w o r k e r " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n @_ 9   < b > V a z i f a l a r : < / b >   ( { l e n ( t a s k s ) }   t a ) \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   i ,   t a s k   i n   e n u m e r a t e ( t a s k s ,   1 ) : 
 
                         s t a t u s _ e m o j i   =   g e t _ s t a t u s _ e m o j i ( t a s k [ ' s t a t u s ' ] ) 
 
                         p r i o r i t y _ e m o j i   =   g e t _ p r i o r i t y _ e m o j i ( t a s k [ ' p r i o r i t y ' ] ) 
 
                         
 
                         t e x t   + =   f " { i } .   { s t a t u s _ e m o j i }   < b > { t a s k [ ' t i t l e ' ] } < / b > \ n " 
 
                         t e x t   + =   f "       { p r i o r i t y _ e m o j i }   { t a s k [ ' p r i o r i t y ' ] }   |   { s t a t u s _ e m o j i }   { t a s k [ ' s t a t u s ' ] } \ n " 
 
                         t e x t   + =   f "       @_ &   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } \ n \ n " 
 
                         
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_   { t a s k [ ' t i t l e ' ] [ : 3 0 ] } . . . " ,   
 
                                         c a l l b a c k _ d a t a = f " v i e w _ t a s k _ { t a s k [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e a r c h _ b y _ w o r k e r " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ s e l e c t _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h l a r n i   t a n l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   B a r c h a   i s h c h i l a r n i   o l i s h 
 
                 w o r k e r s   =   s e l f . d b . g e t _ a c t i v e _ u s e r s ( ) 
 
                 w o r k e r s   =   [ w   f o r   w   i n   w o r k e r s   i f   w [ ' r o l e ' ]   = =   ' W O R K E R ' ] 
 
                 
 
                 i f   n o t   w o r k e r s : 
 
                         t e x t   =   " 2\
  H o z i r c h a   i s h c h i l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " e d i t _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   " @_ �  < b > I s h c h i n i   t a n l a n g : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   w o r k e r   i n   w o r k e r s : 
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " @_ �   { w o r k e r [ ' f u l l _ n a m e ' ] } " ,   
 
                                         c a l l b a c k _ d a t a = f " e d i t _ w o r k e r _ t a s k s _ { w o r k e r [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " e d i t _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ w o r k e r _ t a s k s ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " I s h c h i n i n g   v a z i f a l a r i n i   t a h r i r l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 w o r k e r _ i d   =   i n t ( u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 3 ] ) 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i   o l i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( w o r k e r _ i d ) 
 
                 i f   n o t   w o r k e r : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  I s h c h i   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   I s h c h i n i n g   f a o l   v a z i f a l a r i n i   o l i s h 
 
                 a c t i v e _ s t a t u s e s   =   [ ' R E J A L A S H T I R I L G A N ' ,   ' J A R A Y O N D A ' ,   ' T A S D I Q L A S H _ K U T I L M O Q D A ' ,   ' M U D D A T I _ O T G A N ' ] 
 
                 t a s k s   =   s e l f . d b . g e t _ u s e r _ t a s k s _ b y _ s t a t u s ( w o r k e r _ i d ,   a c t i v e _ s t a t u s e s ) 
 
                 
 
                 i f   n o t   t a s k s : 
 
                         t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n 2\
  H o z i r c h a   f a o l   v a z i f a l a r   y o ' q . " 
 
                         r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( " s e l e c t _ w o r k e r _ t a s k s " ) 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " @_ �   < b > { w o r k e r [ ' f u l l _ n a m e ' ] } < / b > \ n \ n @_: �   < b > T a h r i r l a s h   m u m k i n   b o ' l g a n   v a z i f a l a r : < / b > \ n \ n " 
 
                 
 
                 k e y b o a r d   =   [ ] 
 
                 f o r   i ,   t a s k   i n   e n u m e r a t e ( t a s k s ,   1 ) : 
 
                         s t a t u s _ e m o j i   =   g e t _ s t a t u s _ e m o j i ( t a s k [ ' s t a t u s ' ] ) 
 
                         p r i o r i t y _ e m o j i   =   g e t _ p r i o r i t y _ e m o j i ( t a s k [ ' p r i o r i t y ' ] ) 
 
                         
 
                         t e x t   + =   f " { i } .   { s t a t u s _ e m o j i }   < b > { t a s k [ ' t i t l e ' ] } < / b > \ n " 
 
                         t e x t   + =   f "       { p r i o r i t y _ e m o j i }   { t a s k [ ' p r i o r i t y ' ] }   |   { s t a t u s _ e m o j i }   { t a s k [ ' s t a t u s ' ] } \ n " 
 
                         t e x t   + =   f "       @_ &   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } \ n \ n " 
 
                         
 
                         k e y b o a r d . a p p e n d ( [ 
 
                                 I n l i n e K e y b o a r d B u t t o n ( 
 
                                         f " 2Z?Q  { t a s k [ ' t i t l e ' ] [ : 2 5 ] } . . . " ,   
 
                                         c a l l b a c k _ d a t a = f " e d i t _ t a s k _ { t a s k [ ' i d ' ] } " 
 
                                 ) 
 
                         ] ) 
 
                 
 
                 k e y b o a r d . a p p e n d ( [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = " s e l e c t _ w o r k e r _ t a s k s " ) ] ) 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e d i t _ t a s k ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " V a z i f a n i   t a h r i r l a s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 t a s k _ i d   =   u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 t e x t   =   f " " " 
 
 @_: �   < b > V a z i f a n i   t a h r i r l a s h < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ �   < b > I s h c h i : < / b >   { t a s k . g e t ( ' a s s i g n e d _ n a m e ' ,   ' N o m a \ ' l u m ' ) } 
 
 @_ &   < b > D e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } 
 
 
 
 N i m a n i   t a h r i r l a s h   k e r a k ? 
 
                 " " " 
 
                 
 
                 k e y b o a r d   =   [ 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " 2�   D e a d l i n e   u z a y t i r i s h " ,   c a l l b a c k _ d a t a = f " e x t e n d _ t a s k _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ \  S a r l a v h a   o ' z g a r t i r i s h " ,   c a l l b a c k _ d a t a = f " e d i t _ t i t l e _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_    T a v s i f   o ' z g a r t i r i s h " ,   c a l l b a c k _ d a t a = f " e d i t _ d e s c r i p t i o n _ { t a s k _ i d } " ) ] , 
 
                         [ I n l i n e K e y b o a r d B u t t o n ( " @_ "!  O r q a g a " ,   c a l l b a c k _ d a t a = f " e d i t _ w o r k e r _ t a s k s _ { t a s k [ ' a s s i g n e d _ t o ' ] } " ) ] 
 
                 ] 
 
                 
 
                 r e p l y _ m a r k u p   =   I n l i n e K e y b o a r d M a r k u p ( k e y b o a r d ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ e x t e n d _ t a s k ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " V a z i f a   d e a d l i n e ' i n i   u z a y t i r i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 t a s k _ i d   =   u p d a t e . c a l l b a c k _ q u e r y . d a t a . s p l i t ( ' _ ' ) [ 2 ] 
 
                 
 
                 i f   n o t   s e l f . c h e c k _ p e r m i s s i o n ( u s e r ,   [ U s e r R o l e . S U P E R _ A D M I N ,   U s e r R o l e . A D M I N ] ) : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  B u   f u n k s i y a   f a q a t   a d m i n l a r   u c h u n ! " ) 
 
                         r e t u r n 
 
                 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         r e t u r n 
 
                 
 
                 #   F o y d a l a n u v c h i   h o l a t i n i   o ' r n a t i s h 
 
                 s e l f . u s e r _ s t a t e s [ u s e r [ ' i d ' ] ]   =   f ' e x t e n d i n g _ d e a d l i n e _ { t a s k _ i d } ' 
 
                 
 
                 t e x t   =   f " " " 
 
 2�   < b > D e a d l i n e   u z a y t i r i s h < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > J o r i y   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( t a s k [ ' d e a d l i n e ' ] ) } 
 
 
 
 Q a n c h a   v a q t   q o ' s h i s h   k e r a k ? 
 
 
 
 1 ?Q2S  -   1   s o a t 
 
 2 ?Q2S  -   2   s o a t     
 
 3 ?Q2S  -   3   s o a t 
 
 6 ?Q2S  -   6   s o a t 
 
 1 ?Q2S2 ?Q2S  -   1 2   s o a t 
 
 1 ?Q2Sd   -   1   k u n 
 
 2 ?Q2Sd   -   2   k u n 
 
 3 ?Q2Sd   -   3   k u n 
 
 1 ?Q2Sw   -   1   h a f t a 
 
 
 
 Y o k i   a n i q   v a q t n i   y u b o r i n g   ( m a s a l a n :   2 0 2 4 - 1 2 - 3 1   1 8 : 0 0 ) 
 
                 " " " 
 
                 
 
                 r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( f " e d i t _ t a s k _ { t a s k _ i d } " ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
         
 
         a s y n c   d e f   h a n d l e _ d e a d l i n e _ e x t e n s i o n ( s e l f ,   u p d a t e :   U p d a t e ,   c o n t e x t :   C o n t e x t T y p e s . D E F A U L T _ T Y P E ) : 
 
                 " " " D e a d l i n e   u z a y t i r i s h n i   q a b u l   q i l i s h " " " 
 
                 u s e r   =   s e l f . g e t _ u s e r ( u p d a t e ) 
 
                 
 
                 i f   n o t   s e l f . u s e r _ s t a t e s . g e t ( u s e r [ ' i d ' ] ,   ' ' ) . s t a r t s w i t h ( ' e x t e n d i n g _ d e a d l i n e _ ' ) : 
 
                         r e t u r n 
 
                 
 
                 t a s k _ i d   =   s e l f . u s e r _ s t a t e s [ u s e r [ ' i d ' ] ] . s p l i t ( ' _ ' ) [ 2 ] 
 
                 t a s k   =   s e l f . d b . g e t _ t a s k _ b y _ i d ( t a s k _ i d ) 
 
                 
 
                 i f   n o t   t a s k : 
 
                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  V a z i f a   t o p i l m a d i ! " ) 
 
                         s e l f . u s e r _ s t a t e s . p o p ( u s e r [ ' i d ' ] ,   N o n e ) 
 
                         r e t u r n 
 
                 
 
                 e x t e n s i o n _ t e x t   =   u p d a t e . m e s s a g e . t e x t . s t r i p ( ) 
 
                 n e w _ d e a d l i n e   =   N o n e 
 
                 e x t e n s i o n _ h o u r s   =   0 
 
                 
 
                 #   V a q t   u z a y t i r i s h n i   h i s o b l a s h 
 
                 i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   1 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 2 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 3 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   3 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 6 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   6 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2S2 ?Q2S" : 
 
                         e x t e n s i o n _ h o u r s   =   1 2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   2 4 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 2 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   4 8 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 3 ?Q2Sd " : 
 
                         e x t e n s i o n _ h o u r s   =   7 2 
 
                 e l i f   e x t e n s i o n _ t e x t   = =   " 1 ?Q2Sw " : 
 
                         e x t e n s i o n _ h o u r s   =   1 6 8 
 
                 e l s e : 
 
                         #   A n i q   v a q t   k i r i t i l g a n 
 
                         t r y : 
 
                                 f r o m   d a t e t i m e   i m p o r t   d a t e t i m e 
 
                                 n e w _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( e x t e n s i o n _ t e x t ,   " % Y - % m - % d   % H : % M " ) 
 
                                 n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                         e x c e p t   V a l u e E r r o r : 
 
                                 t r y : 
 
                                         n e w _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( e x t e n s i o n _ t e x t ,   " % d . % m . % Y   % H : % M " ) 
 
                                         n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                                 e x c e p t   V a l u e E r r o r : 
 
                                         a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   " 2\
  N o t o ' g ' r i   f o r m a t !   I l t i m o s ,   q a y t a   u r i n i b   k o ' r i n g . " ) 
 
                                         r e t u r n 
 
                 
 
                 i f   n o t   n e w _ d e a d l i n e : 
 
                         #   S o a t   q o ' s h i s h 
 
                         f r o m   d a t e t i m e   i m p o r t   d a t e t i m e ,   t i m e d e l t a 
 
                         c u r r e n t _ d e a d l i n e   =   d a t e t i m e . s t r p t i m e ( t a s k [ ' d e a d l i n e ' ] ,   " % Y - % m - % d   % H : % M : % S " ) 
 
                         n e w _ d e a d l i n e   =   c u r r e n t _ d e a d l i n e   +   t i m e d e l t a ( h o u r s = e x t e n s i o n _ h o u r s ) 
 
                         n e w _ d e a d l i n e   =   n e w _ d e a d l i n e . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
                 
 
                 #   D a t a b a s e ' d a   d e a d l i n e ' n i   y a n g i l a s h 
 
                 s e l f . d b . e x e c u t e _ u p d a t e ( 
 
                         " U P D A T E   t a s k s   S E T   d e a d l i n e   =   ? ,   u p d a t e d _ a t   =   C U R R E N T _ T I M E S T A M P   W H E R E   i d   =   ? " , 
 
                         ( n e w _ d e a d l i n e ,   t a s k _ i d ) 
 
                 ) 
 
                 
 
                 #   D e a d l i n e   e x t e n s i o n   t a r i x i n i   s a q l a s h 
 
                 s e l f . d b . a d d _ d e a d l i n e _ e x t e n s i o n ( 
 
                         t a s k _ i d = t a s k _ i d , 
 
                         e x t e n d e d _ b y = u s e r [ ' i d ' ] , 
 
                         o l d _ d e a d l i n e = t a s k [ ' d e a d l i n e ' ] , 
 
                         n e w _ d e a d l i n e = n e w _ d e a d l i n e , 
 
                         e x t e n s i o n _ h o u r s = e x t e n s i o n _ h o u r s , 
 
                         r e a s o n = f " A d m i n   t o m o n i d a n   u z a y t i r i l d i :   { u s e r [ ' f u l l _ n a m e ' ] } " 
 
                 ) 
 
                 
 
                 #   A u d i t   l o g 
 
                 s e l f . d b . a d d _ a u d i t _ l o g ( 
 
                         u s e r [ ' i d ' ] ,   
 
                         ' D E A D L I N E _ E X T E N D E D ' ,   
 
                         f " V a z i f a   d e a d l i n e   u z a y t i r i l d i :   { t a s k [ ' t i t l e ' ] }   -   { e x t e n s i o n _ h o u r s }   s o a t   q o ' s h i l d i " 
 
                 ) 
 
                 
 
                 #   I s h c h i g a   x a b a r   y u b o r i s h 
 
                 w o r k e r   =   s e l f . d b . g e t _ u s e r _ b y _ i d ( t a s k [ ' a s s i g n e d _ t o ' ] ) 
 
                 i f   w o r k e r : 
 
                         t r y : 
 
                                 n o t i f i c a t i o n _ t e x t   =   f " " " 
 
 2�   < b > D e a d l i n e   u z a y t i r i l d i ! < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > Y a n g i   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( n e w _ d e a d l i n e ) } 
 
 @_ �   < b > A d m i n : < / b >   { u s e r [ ' f u l l _ n a m e ' ] } 
 
 
 
 V a z i f a   m u d d a t i   u z a y t i r i l d i . 
 
                                 " " " 
 
                                 
 
                                 a w a i t   c o n t e x t . b o t . s e n d _ m e s s a g e ( 
 
                                         c h a t _ i d = w o r k e r [ ' t e l e g r a m _ i d ' ] , 
 
                                         t e x t = n o t i f i c a t i o n _ t e x t , 
 
                                         p a r s e _ m o d e = ' H T M L ' 
 
                                 ) 
 
                         e x c e p t   E x c e p t i o n   a s   e : 
 
                                 l o g g e r . e r r o r ( f " I s h c h i g a   x a b a r   y u b o r i s h d a   x a t o l i k :   { e } " ) 
 
                 
 
                 t e x t   =   f " " " 
 
 2Z&   < b > D e a d l i n e   u z a y t i r i l d i ! < / b > 
 
 
 
 @_ \  < b > V a z i f a : < / b >   { t a s k [ ' t i t l e ' ] } 
 
 @_ &   < b > Y a n g i   d e a d l i n e : < / b >   { f o r m a t _ d a t e t i m e ( n e w _ d e a d l i n e ) } 
 
 2�   < b > Q o ' s h i l g a n   v a q t : < / b >   { e x t e n s i o n _ h o u r s }   s o a t 
 
 
 
 I s h c h i g a   x a b a r   y u b o r i l d i . 
 
                 " " " 
 
                 
 
                 s e l f . u s e r _ s t a t e s . p o p ( u s e r [ ' i d ' ] ,   N o n e ) 
 
                 r e p l y _ m a r k u p   =   s e l f . c r e a t e _ b a c k _ b u t t o n ( f " e d i t _ w o r k e r _ t a s k s _ { t a s k [ ' a s s i g n e d _ t o ' ] } " ) 
 
                 a w a i t   s e l f . s e n d _ m e s s a g e ( u p d a t e ,   c o n t e x t ,   t e x t ,   r e p l y _ m a r k u p ) 
 
 
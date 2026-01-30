import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import Database
from utils import get_uzbek_time, calculate_time_remaining, get_status_emoji, get_priority_emoji, format_datetime
from config import TaskStatus, REMINDER_INTERVAL_HOURS, DEADLINE_WARNING_HOURS, DEFAULT_PENALTY_AMOUNT

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot
        self.is_running = False
        # Oxirgi ogohlantirish vaqtini saqlash: {task_id: last_reminder_time}
        self.last_reminder_times = {}
    
    async def start_notifications(self):
        """Eslatmalar tizimini ishga tushirish"""
        self.is_running = True
        logger.info("Eslatmalar tizimi ishga tushdi")
        
        while self.is_running:
            try:
                await self.check_and_send_notifications()
                await asyncio.sleep(60)  # Har minut tekshirish
            except Exception as e:
                logger.error(f"Eslatmalar tizimida xatolik: {e}")
                await asyncio.sleep(60)
    
    async def stop_notifications(self):
        """Eslatmalar tizimini to'xtatish"""
        self.is_running = False
        logger.info("Eslatmalar tizimi to'xtatildi")
    
    async def check_and_send_notifications(self):
        """Eslatmalarni tekshirish va yuborish"""
        try:
            # Faol vazifalarni olish
            active_tasks = self.get_active_tasks()
            
            for task in active_tasks:
                await self.check_task_notifications(task)
            
            # Muddati o'tgan vazifalarni tekshirish
            await self.check_overdue_tasks()
            
        except Exception as e:
            logger.error(f"Eslatmalarni tekshirishda xatolik: {e}")
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Faol vazifalarni olish"""
        query = """
            SELECT t.*, u.telegram_id, u.full_name as assigned_name
            FROM tasks t
            JOIN users u ON t.assigned_to = u.id
            WHERE t.status IN ('REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA')
            AND u.is_active = TRUE
        """
        return self.db.execute_query(query)
    
    async def check_task_notifications(self, task: Dict[str, Any]):
        """Vazifa uchun eslatmalarni tekshirish"""
        try:
            now = get_uzbek_time()
            
            # Deadline ni to'g'ri parse qilish
            if isinstance(task['deadline'], str):
                deadline = datetime.fromisoformat(task['deadline'])
            elif isinstance(task['deadline'], datetime):
                deadline = task['deadline']
            else:
                logger.error(f"Noto'g'ri deadline format: {type(task['deadline'])}")
                return
            
            if deadline.tzinfo is None:
                from pytz import timezone
                deadline = timezone('Asia/Tashkent').localize(deadline)
            
            # Vazifa boshlanish vaqtini tekshirish
            if task['status'] == 'REJALASHTIRILGAN':
                if isinstance(task['start_at'], str):
                    start_time = datetime.fromisoformat(task['start_at'])
                elif isinstance(task['start_at'], datetime):
                    start_time = task['start_at']
                else:
                    logger.error(f"Noto'g'ri start_at format: {type(task['start_at'])}")
                    return
                    
                if start_time.tzinfo is None:
                    from pytz import timezone
                    start_time = timezone('Asia/Tashkent').localize(start_time)
                
                if now >= start_time:
                    # Vazifani JARAYONDA holatiga o'tkazish
                    self.db.update_task_status(task['id'], 'JARAYONDA')
                    # Statusni yangilash
                    task['status'] = 'JARAYONDA'
                    
                    # Eslatma yuborish
                    await self.send_task_started_notification(task)
            
            # Deadline eslatmalari
            time_remaining = deadline - now
            hours_remaining = time_remaining.total_seconds() / 3600
            
            if hours_remaining > 0:
                # Sozlamadan interval olish
                settings = self.db.get_org_settings()
                reminder_interval_minutes = settings.get('reminder_interval_minutes', 180) if settings else 180  # Default 3 soat
                reminder_interval_hours = reminder_interval_minutes / 60
                
                # Faol vazifalarni sozlamadan interval bo'yicha qayta yuborish
                if task['status'] in ['JARAYONDA', 'REJALASHTIRILGAN']:
                    await self.check_periodic_reminder(task, reminder_interval_minutes)
                
                # Deadline yaqinlashganda eslatmalar
                for warning_hours in DEADLINE_WARNING_HOURS:
                    if warning_hours - 0.1 <= hours_remaining <= warning_hours + 0.1:
                        await self.send_deadline_warning(task, warning_hours)
            
        except Exception as e:
            logger.error(f"Vazifa eslatmalarini tekshirishda xatolik: {e}")
    
    async def check_overdue_tasks(self):
        """Muddati o'tgan vazifalarni tekshirish"""
        try:
            overdue_tasks = self.db.get_overdue_tasks()
            
            for task in overdue_tasks:
                if task['status'] != TaskStatus.OVERDUE:
                    # Statusni MUDDATI_OTGAN ga o'zgartirish (TaskStatus.OVERDUE = 'MUDDATI_OTGAN')
                    self.db.update_task_status(task['id'], TaskStatus.OVERDUE)
                    
                    # Jarima qo'shish
                    if not task['is_penalized']:
                        self.add_penalty(task)
                    
                    # Eslatma yuborish
                    await self.send_overdue_notification(task)
        
        except Exception as e:
            logger.error(f"Muddati o'tgan vazifalarni tekshirishda xatolik: {e}")
    
    def add_penalty(self, task: Dict[str, Any]):
        """Jarima qo'shish"""
        try:
            query = """
                UPDATE tasks 
                SET is_penalized = TRUE, penalty_amount = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.db.execute_update(query, (DEFAULT_PENALTY_AMOUNT, task['id']))
            
            # Audit log
            self.db.add_audit_log(
                task['assigned_to'], 
                'PENALTY_ADDED', 
                f"Jarima qo'shildi: {task['title']} - {DEFAULT_PENALTY_AMOUNT} UZS"
            )
            
        except Exception as e:
            logger.error(f"Jarima qo'shishda xatolik: {e}")
    
    async def send_task_started_notification(self, task: Dict[str, Any]):
        """Vazifa boshlangan eslatma"""
        try:
            # Deadline ni formatlash
            if isinstance(task['deadline'], str):
                deadline = datetime.fromisoformat(task['deadline'])
                deadline_str = format_datetime(deadline)
            elif isinstance(task['deadline'], datetime):
                deadline_str = format_datetime(task['deadline'])
            else:
                deadline_str = str(task['deadline'])
            
            text = f"""
🚀 <b>Vazifa boshladi!</b>

📝 <b>Sarlavha:</b> {task['title']}
⏰ <b>Deadline:</b> {deadline_str}
{get_priority_emoji(task['priority'])} <b>Ustuvorlik:</b> {task['priority']}

Vazifani bajarishni boshlang!
            """
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Vazifa boshlanish eslatmasini yuborishda xatolik: {e}")
    
    async def send_reminder_notification(self, task: Dict[str, Any], hours_remaining: float):
        """3 soatlik eslatma"""
        try:
            time_text = calculate_time_remaining(task['deadline'])
            
            text = f"""
⏰ <b>Eslatma</b>

📝 <b>Vazifa:</b> {task['title']}
⏱ <b>Qolgan vaqt:</b> {time_text}

Vazifani davom ettiring!
            """
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Eslatma yuborishda xatolik: {e}")
    
    async def check_periodic_reminder(self, task: Dict[str, Any], interval_minutes: int):
        """Sozlamadan interval bo'yicha vazifalarni qayta yuborish"""
        try:
            if not self.bot:
                logger.warning("Bot None, eslatma yuborib bo'lmadi")
                return
                
            task_id = task['id']
            now = get_uzbek_time()
            
            # Oxirgi ogohlantirish vaqtini olish
            last_reminder = self.last_reminder_times.get(task_id)
            
            # Agar oxirgi ogohlantirish yo'q bo'lsa, vazifaning yaratilgan vaqtini ishlatish
            if last_reminder is None:
                # created_at ni to'g'ri parse qilish
                if isinstance(task['created_at'], str):
                    created_at = datetime.fromisoformat(task['created_at'])
                elif isinstance(task['created_at'], datetime):
                    created_at = task['created_at']
                else:
                    logger.error(f"Noto'g'ri created_at format: {type(task['created_at'])}")
                    return
                    
                if created_at.tzinfo is None:
                    from pytz import timezone
                    created_at = timezone('Asia/Tashkent').localize(created_at)
                
                last_reminder = created_at
            
            # Vaqt farqini minutlarda hisoblash
            time_since_last_reminder = (now - last_reminder).total_seconds() / 60
            
            task_title = task.get('title', 'Noma\'lum')
            logger.debug(f"Periodik eslatma tekshiruvi: task={task_title}, interval={interval_minutes} min, time_since_last={time_since_last_reminder:.1f} min")
            
            # Agar interval o'tgan bo'lsa, ogohlantirish yuborish
            if time_since_last_reminder >= interval_minutes:
                # Ogohlantirish yuborish
                await self.send_periodic_task_reminder(task, interval_minutes)
                
                # Oxirgi ogohlantirish vaqtini yangilash
                self.last_reminder_times[task_id] = now
                
                logger.info(f"✅ Periodik eslatma yuborildi: {task_title}, interval: {interval_minutes} minut, time_since_last: {time_since_last_reminder:.1f} minut")
            else:
                logger.debug(f"Periodik eslatma o'tkazib yuborildi: time_since_last={time_since_last_reminder:.1f} < interval={interval_minutes}")
                
        except Exception as e:
            logger.error(f"Periodik eslatmani tekshirishda xatolik: {e}", exc_info=True)
    
    async def send_periodic_task_reminder(self, task: Dict[str, Any], interval_minutes: int):
        """Periodik vazifa eslatmasini yuborish"""
        try:
            if not self.bot:
                logger.error("Bot None, eslatma yuborib bo'lmadi")
                return
            
            time_text = calculate_time_remaining(task['deadline'])
            priority_emoji = get_priority_emoji(task['priority'])
            status_emoji = get_status_emoji(task['status'])
            
            # Intervalni formatlash
            interval_hours = interval_minutes // 60
            interval_mins = interval_minutes % 60
            if interval_hours > 0 and interval_mins > 0:
                interval_text = f"{interval_hours} soat {interval_mins} minut"
            elif interval_hours > 0:
                interval_text = f"{interval_hours} soat"
            else:
                interval_text = f"{interval_mins} minut"
            
            text = f"""
🔔 <b>Vazifa eslatmasi</b>

📝 <b>Vazifa:</b> {task['title']}
{status_emoji} <b>Holat:</b> {task['status']}
{priority_emoji} <b>Ustuvorlik:</b> {task['priority']}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])}
⏱ <b>Qolgan vaqt:</b> {time_text}

<i>Bu eslatma har {interval_text}da yuboriladi.</i>

Vazifani davom ettiring!
            """
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            assigned_name = task.get('assigned_name', 'Noma\'lum')
            logger.info(f"Periodik eslatma yuborildi: {task['title']} -> {assigned_name}")
            
        except Exception as e:
            logger.error(f"Periodik eslatma yuborishda xatolik: {e}")
    
    async def send_deadline_warning(self, task: Dict[str, Any], hours: int):
        """Deadline yaqinlashganda eslatma"""
        try:
            if hours == 24:
                emoji = "⚠️"
                text_hours = "24 soat"
            elif hours == 3:
                emoji = "🚨"
                text_hours = "3 soat"
            elif hours == 1:
                emoji = "🔥"
                text_hours = "1 soat"
            else:
                return
            
            text = f"""
{emoji} <b>Jiddiy eslatma!</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Qolgan vaqt:</b> {text_hours}

Tezroq ishlang!
            """
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Deadline eslatmasini yuborishda xatolik: {e}")
    
    async def send_overdue_notification(self, task: Dict[str, Any]):
        """Muddati o'tgan eslatma"""
        try:
            text = f"""
🚨 <b>MUDDATI O'TGAN!</b>

📝 <b>Vazifa:</b> {task['title']}
⏰ <b>Deadline:</b> {format_datetime(task['deadline'])}
💰 <b>Jarima:</b> {DEFAULT_PENALTY_AMOUNT:,} UZS

Vazifa muddati o'tdi va jarima qo'shildi!
            """
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Muddati o'tgan eslatmasini yuborishda xatolik: {e}")
    
    async def send_penalty_notification(self, task: Dict[str, Any], penalty_amount: int):
        """Jarima haqida eslatma"""
        try:
            text = f"""
💰 <b>Jarima qo'shildi</b>

📝 <b>Vazifa:</b> {task['title']}
💸 <b>Jarima miqdori:</b> {penalty_amount:,} UZS

Vazifa muddati o'tgani uchun jarima qo'shildi.
            """
            
            await self.bot.send_message(
                chat_id=task['telegram_id'],
                text=text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Jarima eslatmasini yuborishda xatolik: {e}")

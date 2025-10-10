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
            WHERE t.status IN ('SCHEDULED', 'IN_PROGRESS', 'WAITING_APPROVAL')
            AND u.is_active = 1
        """
        return self.db.execute_query(query)
    
    async def check_task_notifications(self, task: Dict[str, Any]):
        """Vazifa uchun eslatmalarni tekshirish"""
        try:
            now = get_uzbek_time()
            deadline = datetime.fromisoformat(task['deadline'])
            
            if deadline.tzinfo is None:
                from pytz import timezone
                deadline = timezone('Asia/Tashkent').localize(deadline)
            
            # Vazifa boshlanish vaqtini tekshirish
            if task['status'] == 'SCHEDULED':
                start_time = datetime.fromisoformat(task['start_at'])
                if start_time.tzinfo is None:
                    from pytz import timezone
                    start_time = timezone('Asia/Tashkent').localize(start_time)
                
                if now >= start_time:
                    # Vazifani IN_PROGRESS holatiga o'tkazish
                    self.db.update_task_status(task['id'], 'IN_PROGRESS')
                    
                    # Eslatma yuborish
                    await self.send_task_started_notification(task)
            
            # Deadline eslatmalari
            time_remaining = deadline - now
            hours_remaining = time_remaining.total_seconds() / 3600
            
            if hours_remaining > 0:
                # 3 soatlik eslatmalar
                if hours_remaining <= REMINDER_INTERVAL_HOURS and task['status'] == 'IN_PROGRESS':
                    await self.send_reminder_notification(task, hours_remaining)
                
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
                if task['status'] != 'OVERDUE':
                    # Statusni OVERDUE ga o'zgartirish
                    self.db.update_task_status(task['id'], 'OVERDUE')
                    
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
                SET is_penalized = 1, penalty_amount = ?, updated_at = CURRENT_TIMESTAMP
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
            text = f"""
🚀 <b>Vazifa boshladi!</b>

📝 <b>Sarlavha:</b> {task['title']}
⏰ <b>Deadline:</b> {format_datetime(deadline)}
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

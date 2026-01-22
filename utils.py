import pytz
from datetime import datetime, timedelta
from typing import Optional
import ulid
from config import DEFAULT_TIMEZONE

def generate_task_id() -> str:
    """Vazifa uchun unique ID yaratish"""
    return str(ulid.new())

def get_uzbek_time() -> datetime:
    """O'zbekiston vaqtini olish"""
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    return datetime.now(tz)

def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Sana va vaqtni formatlash"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime(format_str)

def parse_datetime(date_str: str) -> Optional[datetime]:
    """Sana matnini datetime obyektiga aylantirish"""
    try:
        # Turli formatlarni sinab ko'rish
        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    except:
        return None

def is_future_datetime(dt: datetime) -> bool:
    """Kelajakdagi vaqt ekanligini tekshirish"""
    now = get_uzbek_time()
    
    # Agar dt timezone-siz bo'lsa, uni timezone-li qilish
    if dt.tzinfo is None:
        tz = pytz.timezone(DEFAULT_TIMEZONE)
        dt = tz.localize(dt)
    
    return dt > now

def calculate_time_remaining(deadline: datetime) -> str:
    """Qolgan vaqtni hisoblash"""
    now = get_uzbek_time()
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline)
    
    if deadline.tzinfo is None:
        deadline = pytz.timezone(DEFAULT_TIMEZONE).localize(deadline)
    
    remaining = deadline - now
    
    if remaining.total_seconds() <= 0:
        return "⏰ Muddati o'tgan"
    
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"📅 {days} kun, {hours} soat qoldi"
    elif hours > 0:
        return f"⏰ {hours} soat, {minutes} daqiqa qoldi"
    else:
        return f"⏰ {minutes} daqiqa qoldi"

def get_priority_emoji(priority: str) -> str:
    """Ustuvorlik uchun emoji"""
    priority_emojis = {
        'PAST': '🟢',
        'ORTA': '🟡', 
        'YUQORI': '🟠',
        'KRITIK': '🔴',
        # Eski ingliz tilidagi qiymatlar uchun ham qo'llab-quvvatlash
        'LOW': '🟢',
        'MEDIUM': '🟡', 
        'HIGH': '🟠',
        'CRITICAL': '🔴'
    }
    return priority_emojis.get(priority, '⚪')

def get_status_emoji(status: str) -> str:
    """Status uchun emoji"""
    status_emojis = {
        'REJALASHTIRILGAN': '📅',
        'JARAYONDA': '🔄',
        'TASDIQLASH_KUTILMOQDA': '⏳',
        'BAJARILDI': '✅',
        'RAD_ETILDI': '❌',
        'MUDDATI_OTGAN': '🚨',
        # Eski ingliz tilidagi qiymatlar uchun ham qo'llab-quvvatlash
        'SCHEDULED': '📅',
        'IN_PROGRESS': '🔄',
        'WAITING_APPROVAL': '⏳',
        'DONE': '✅',
        'REJECTED': '❌',
        'OVERDUE': '🚨'
    }
    return status_emojis.get(status, '❓')

def mask_phone_number(phone: str) -> str:
    """Telefon raqamini yashirish"""
    if not phone or len(phone) < 8:
        return phone
    
    if len(phone) >= 8:
        return phone[:4] + '****' + phone[-4:]
    return phone

def format_penalty_amount(amount: int) -> str:
    """Jarima miqdorini formatlash"""
    return f"{amount:,} UZS".replace(',', ' ')

def is_work_hours() -> bool:
    """Ish vaqti ekanligini tekshirish"""
    now = get_uzbek_time()
    work_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    work_end = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return work_start <= now <= work_end

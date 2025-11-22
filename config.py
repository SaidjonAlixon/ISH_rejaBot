import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = 'sqlite:///ishbot.db'

# Kanal sozlamalari
WORK_START_CHANNEL_ID = os.getenv('WORK_START_CHANNEL_ID')  # Ish boshlangan kanal ID
WORK_END_CHANNEL_ID = os.getenv('WORK_END_CHANNEL_ID')  # Ish tugagan kanal ID

# Super Admin ID (ixtiyoriy)
SUPER_ADMIN_TELEGRAM_ID_STR = os.getenv('SUPER_ADMIN_TELEGRAM_ID')
SUPER_ADMIN_TELEGRAM_ID = int(SUPER_ADMIN_TELEGRAM_ID_STR) if SUPER_ADMIN_TELEGRAM_ID_STR else None

# Tashkilot sozlamalari
DEFAULT_TIMEZONE = 'Asia/Tashkent'
DEFAULT_PENALTY_AMOUNT = 1000000  # 1,000,000 UZS
WORK_HOURS_START = 9  # 09:00
WORK_HOURS_END = 18   # 18:00

# Eslatmalar
REMINDER_INTERVAL_HOURS = 3
DEADLINE_WARNING_HOURS = [24, 3, 1]  # qancha soat qolganda eslatish

# Foydalanuvchi rollari
class UserRole:
    SUPER_ADMIN = 'SUPER_ADMIN'
    ADMIN = 'ADMIN'
    WORKER = 'WORKER'

# Vazifa statuslari
class TaskStatus:
    SCHEDULED = 'REJALASHTIRILGAN'
    IN_PROGRESS = 'JARAYONDA'
    WAITING_APPROVAL = 'TASDIQLASH_KUTILMOQDA'
    DONE = 'BAJARILDI'
    REJECTED = 'RAD_ETILDI'
    OVERDUE = 'MUDDATI_OTGAN'

# Vazifa ustuvorligi
class TaskPriority:
    LOW = 'PAST'
    MEDIUM = 'ORTA'
    HIGH = 'YUQORI'
    CRITICAL = 'KRITIK'
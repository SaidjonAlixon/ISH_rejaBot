import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
# PostgreSQL database URL
# Format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ishbot')

# Kanal sozlamalari
WORK_START_CHANNEL_ID = os.getenv('WORK_START_CHANNEL_ID')  # Ish boshlangan kanal ID
WORK_END_CHANNEL_ID = os.getenv('WORK_END_CHANNEL_ID')  # Ish tugagan kanal ID

# Super Admin ID (ixtiyoriy) - bir nechta ID larni vergul bilan ajratib yozish mumkin
# Masalan: SUPER_ADMIN_TELEGRAM_ID=123456789,987654321,555666777
SUPER_ADMIN_TELEGRAM_ID_STR = os.getenv('SUPER_ADMIN_TELEGRAM_ID')
if SUPER_ADMIN_TELEGRAM_ID_STR:
    # Vergul bilan ajratilgan ID larni ro'yxatga o'tkazish
    SUPER_ADMIN_TELEGRAM_IDS = [int(id_str.strip()) for id_str in SUPER_ADMIN_TELEGRAM_ID_STR.split(',') if id_str.strip()]
else:
    SUPER_ADMIN_TELEGRAM_IDS = []

# Orqaga moslik uchun (eski kodlar uchun)
SUPER_ADMIN_TELEGRAM_ID = SUPER_ADMIN_TELEGRAM_IDS[0] if SUPER_ADMIN_TELEGRAM_IDS else None

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
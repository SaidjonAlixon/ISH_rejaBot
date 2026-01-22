from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import format_datetime, get_uzbek_time
import logging

logger = logging.getLogger(__name__)

class TaskNotificationHandler:
    def __init__(self, db):
        self.db = db
    
    async def notify_worker_task_approved(self, task, admin, context: ContextTypes.DEFAULT_TYPE):
        """Ishchiga vazifa tasdiqlanganini xabar qilish"""
        try:
            # Ishchini olish
            worker = self.db.get_user_by_id(task['assigned_to'])
            if not worker:
                logger.error(f"Ishchi topilmadi: {task['assigned_to']}")
                return
            
            notification_text = f"""
🎉 <b>Vazifangiz tasdiqlandi!</b>

📝 <b>Vazifa:</b> {task['title']}
✅ <b>Holat:</b> BAJARILDI
👤 <b>Tasdiqlovchi:</b> {admin['full_name']}
📅 <b>Tasdiqlangan vaqt:</b> {format_datetime(get_uzbek_time())}

Tabriklaymiz! Vazifangiz muvaffaqiyatli yakunlandi! 🎊
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task['id']}")
                ],
                [
                    InlineKeyboardButton("✅ Bajarilgan ishlar", callback_data="completed_tasks")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=worker['telegram_id'],
                text=notification_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            logger.info(f"Tasdiqlash xabari yuborildi ishchiga: {worker['full_name']}")
            
        except Exception as e:
            logger.error(f"Ishchiga tasdiqlash xabari yuborishda xatolik: {e}")
    
    async def notify_worker_task_rejected(self, task, admin, context: ContextTypes.DEFAULT_TYPE, resubmit_count: int = 0):
        """Ishchiga vazifa rad etilganini xabar qilish"""
        try:
            # Ishchini olish
            worker = self.db.get_user_by_id(task['assigned_to'])
            if not worker:
                logger.error(f"Ishchi topilmadi: {task['assigned_to']}")
                return
            
            # Qayta yuborish imkoniyati
            remaining_attempts = 3 - resubmit_count
            can_resubmit = self.db.can_resubmit_task(task['id'])
            
            notification_text = f"""
❌ <b>Vazifangiz rad etildi</b>

📝 <b>Vazifa:</b> {task['title']}
🚫 <b>Holat:</b> RAD ETILDI
👤 <b>Rad etuvchi:</b> {admin['full_name']}
📅 <b>Rad etilgan vaqt:</b> {format_datetime(get_uzbek_time())}
🔄 <b>Qayta yuborish:</b> {resubmit_count}/3 marta

"""
            
            if not can_resubmit:
                notification_text += """
⚠️ <b>DIQQAT!</b>
Vazifangiz 3 marta rad etildi va qayta yuborish imkoniyati tugadi!
💰 <b>Shtraf:</b> 1,000,000 so'm
                """
            elif remaining_attempts > 0:
                notification_text += f"""
Iltimos, vazifani qayta ko'rib chiqing va kerak bo'lsa qayta yuboring.
⚠️ <b>Qolgan imkoniyat:</b> {remaining_attempts} marta
                """
            
            keyboard = [
                [
                    InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task['id']}")
                ]
            ]
            
            # Agar qayta yuborish mumkin bo'lsa, tugma qo'shish
            if can_resubmit:
                keyboard.append([
                    InlineKeyboardButton("🔄 Qayta yuborish", callback_data=f"resubmit_task_{task['id']}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Bajarilmagan vaqt o'tgan", callback_data="failed_tasks")
            ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=worker['telegram_id'],
                text=notification_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            logger.info(f"Rad etish xabari yuborildi ishchiga: {worker['full_name']}")
            
        except Exception as e:
            logger.error(f"Ishchiga rad etish xabari yuborishda xatolik: {e}")
    
    async def notify_admins_task_failed(self, task, worker, context: ContextTypes.DEFAULT_TYPE):
        """Admin'larga vazifa bajarilmaganligini xabar qilish"""
        try:
            # Admin'larni olish
            admins = self.db.get_active_users()
            admins = [a for a in admins if a['role'] in ['SUPER_ADMIN', 'ADMIN']]
            
            notification_text = f"""
❌ <b>Vazifa bajarilmadi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Ishchi:</b> {worker['full_name']}
📅 <b>Vaqt:</b> {format_datetime(get_uzbek_time())}

Vazifa bajarilmagan deb belgilandi.
            """
            
            for admin in admins:
                try:
                    await context.bot.send_message(
                        chat_id=admin['telegram_id'],
                        text=notification_text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Admin'ga xabar yuborishda xatolik: {e}")
            
            logger.info(f"Vazifa bajarilmaganligi haqida xabar yuborildi {len(admins)} ta admin'ga")
            
        except Exception as e:
            logger.error(f"Admin'larga xabar yuborishda xatolik: {e}")
    
    async def notify_admins_extension_request(self, task, worker, reason, context: ContextTypes.DEFAULT_TYPE):
        """Admin'larga deadline uzaytirish so'rovini xabar qilish"""
        try:
            # Admin'larni olish
            admins = self.db.get_active_users()
            admins = [a for a in admins if a['role'] in ['SUPER_ADMIN', 'ADMIN']]
            
            notification_text = f"""
⏰ <b>Deadline uzaytirish so'rovi</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Ishchi:</b> {worker['full_name']}
⏰ <b>Joriy deadline:</b> {format_datetime(task['deadline'])}
📄 <b>Sabab:</b> {reason}
📅 <b>So'rov vaqti:</b> {format_datetime(get_uzbek_time())}
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Qabul qilish", callback_data=f"approve_extension_{task['id']}")],
                [InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_extension_{task['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            for admin in admins:
                try:
                    await context.bot.send_message(
                        chat_id=admin['telegram_id'],
                        text=notification_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Admin'ga xabar yuborishda xatolik: {e}")
            
            logger.info(f"Deadline uzaytirish so'rovi yuborildi {len(admins)} ta admin'ga")
            
        except Exception as e:
            logger.error(f"Admin'larga xabar yuborishda xatolik: {e}")
    
    async def notify_admins_task_completed(self, task, worker, context: ContextTypes.DEFAULT_TYPE):
        """Admin'larga vazifa tugatilganini xabar qilish"""
        try:
            # Admin'larni olish
            admins = self.db.get_active_users()
            admins = [a for a in admins if a['role'] in ['SUPER_ADMIN', 'ADMIN']]
            
            notification_text = f"""
✅ <b>Vazifa tugatildi!</b>

📝 <b>Vazifa:</b> {task['title']}
👤 <b>Ishchi:</b> {worker['full_name']}
📅 <b>Tugatilgan vaqt:</b> {format_datetime(get_uzbek_time())}

Ishchi vazifani tugatgan. Tasdiqlash kutilmoqda.
            """
            
            keyboard = [
                [InlineKeyboardButton("👁 Vazifani ko'rish", callback_data=f"view_task_{task['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            for admin in admins:
                try:
                    await context.bot.send_message(
                        chat_id=admin['telegram_id'],
                        text=notification_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Admin'ga xabar yuborishda xatolik: {e}")
            
            logger.info(f"Vazifa tugatilgani haqida xabar yuborildi {len(admins)} ta admin'ga")
            
        except Exception as e:
            logger.error(f"Admin'larga xabar yuborishda xatolik: {e}")
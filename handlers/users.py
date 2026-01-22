from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base import BaseHandler
from config import UserRole
from utils import mask_phone_number
import logging

logger = logging.getLogger(__name__)

class UserHandler(BaseHandler):
    def __init__(self, db):
        super().__init__(db)
        self.user_states = {}
    
    async def handle_users_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchilar menyusi"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        text = """
👥 <b>Foydalanuvchilar boshqaruvi</b>

Quyidagi amallardan birini tanlang:
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton("👷 Ishchi qo'shish", callback_data="add_worker")],
            [InlineKeyboardButton("📋 Foydalanuvchilar ro'yxati", callback_data="list_users")],
            [InlineKeyboardButton("🔄 Rollarni tahrirlash", callback_data="edit_roles")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin qo'shish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        self.user_states[user['id']] = 'adding_admin'
        
        text = """
👨‍💼 <b>Admin qo'shish</b>

Yangi adminning Telegram ID yoki username'ini yuboring:
        """
        
        reply_markup = self.create_back_button("users_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_add_worker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ishchi qo'shish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        self.user_states[user['id']] = 'adding_worker'
        
        text = """
👷 <b>Ishchi qo'shish</b>

Yangi ishchining Telegram ID yoki username'ini yuboring:
        """
        
        reply_markup = self.create_back_button("users_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_user_identifier(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi identifikatorini qabul qilish"""
        user = self.get_user(update)
        
        if self.user_states.get(user['id']) not in ['adding_admin', 'adding_worker']:
            return
        
        identifier = update.message.text.strip()
        
        # Telegram ID yoki username'ni tekshirish
        try:
            if identifier.isdigit():
                # Telegram ID
                telegram_id = int(identifier)
                target_user = self.db.get_user_by_telegram_id(telegram_id)
            else:
                # Username
                if identifier.startswith('@'):
                    identifier = identifier[1:]
                
                # Username bo'yicha qidirish
                users = self.db.get_all_users()
                target_user = None
                for u in users:
                    if u['username'] == identifier:
                        target_user = u
                        break
                
                if not target_user:
                    await self.send_message(update, context, "❌ Foydalanuvchi topilmadi!")
                    return
        except ValueError:
            await self.send_message(update, context, "❌ Noto'g'ri format! Telegram ID (raqam) yoki username yuboring.")
            return
        
        if not target_user:
            await self.send_message(update, context, "❌ Foydalanuvchi topilmadi!")
            return
        
        # Rol tayinlash
        new_role = UserRole.ADMIN if self.user_states[user['id']] == 'adding_admin' else UserRole.WORKER
        
        # Rolni yangilash
        self.db.update_user_role(target_user['id'], new_role)
        
        # Holatni tozalash
        del self.user_states[user['id']]
        
        # Audit log
        self.db.add_audit_log(
            user['id'], 
            'USER_ROLE_UPDATED', 
            f"Foydalanuvchi roli yangilandi: {target_user['full_name']} -> {new_role}"
        )
        
        role_name = "Admin" if new_role == UserRole.ADMIN else "Ishchi"
        
        text = f"""
✅ <b>Foydalanuvchi roli yangilandi!</b>

👤 <b>Foydalanuvchi:</b> {target_user['full_name']}
🆔 <b>Telegram ID:</b> {target_user['telegram_id']}
📱 <b>Username:</b> @{target_user['username'] or 'Yoq'}
🎭 <b>Yangi rol:</b> {role_name}
        """
        
        reply_markup = self.create_back_button("users_menu")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_edit_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Rollarni tahrirlash - foydalanuvchilar ro'yxatini ko'rsatish"""
        # Bu funksiya list_users bilan bir xil
        await self.handle_list_users(update, context)
    
    async def handle_list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchilar ro'yxati"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        users = self.db.get_all_users()
        
        if not users:
            text = "📝 Hozircha foydalanuvchilar yo'q."
            reply_markup = self.create_back_button("users_menu")
            await self.send_message(update, context, text, reply_markup)
            return
        
        text = f"👥 <b>Foydalanuvchilar ro'yxati</b> ({len(users)} ta)\n\n"
        
        for i, u in enumerate(users, 1):
            role_emoji = "👑" if u['role'] == UserRole.SUPER_ADMIN else "👨‍💼" if u['role'] == UserRole.ADMIN else "👷"
            status_emoji = "✅" if u['is_active'] else "❌"
            phone = mask_phone_number(u['phone']) if u['phone'] else "Yo'q"
            
            text += f"""
{i}. {role_emoji} <b>{u['full_name']}</b> {status_emoji}
🆔 ID: {u['telegram_id']} | 📱 @{u['username'] or 'Yoq'}
📞 {phone} | 🎭 {u['role']}

"""
        
        keyboard = []
        for u in users:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {u['full_name']}", 
                    callback_data=f"user_details_{u['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="users_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_user_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi tafsilotlari"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        user_id = int(update.callback_query.data.split('_')[2])
        
        # Foydalanuvchini topish
        users = self.db.get_all_users()
        target_user = None
        for u in users:
            if u['id'] == user_id:
                target_user = u
                break
        
        if not target_user:
            await self.send_message(update, context, "❌ Foydalanuvchi topilmadi!")
            return
        
        role_emoji = "👑" if target_user['role'] == UserRole.SUPER_ADMIN else "👨‍💼" if target_user['role'] == UserRole.ADMIN else "👷"
        status_emoji = "✅" if target_user['is_active'] else "❌"
        phone = mask_phone_number(target_user['phone']) if target_user['phone'] else "Yo'q"
        
        text = f"""
👤 <b>Foydalanuvchi tafsilotlari</b>

{role_emoji} <b>Ism:</b> {target_user['full_name']}
🆔 <b>Telegram ID:</b> {target_user['telegram_id']}
📱 <b>Username:</b> @{target_user['username'] or 'Yoq'}
📞 <b>Telefon:</b> {phone}
🎭 <b>Rol:</b> {target_user['role']}
{status_emoji} <b>Holat:</b> {'Faol' if target_user['is_active'] else 'Nofaol'}
📅 <b>Ro'yxatdan o'tgan:</b> {target_user['created_at']}
        """
        
        keyboard = []
        
        # Rol o'zgartirish tugmalari
        if target_user['role'] != UserRole.SUPER_ADMIN:
            if target_user['role'] != UserRole.ADMIN:
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 Admin qilish", callback_data=f"make_admin_{user_id}")
                ])
            if target_user['role'] != UserRole.WORKER:
                keyboard.append([
                    InlineKeyboardButton("👷 Ishchi qilish", callback_data=f"make_worker_{user_id}")
                ])
        
        # Faollik o'zgartirish
        if target_user['is_active']:
            keyboard.append([
                InlineKeyboardButton("❌ Nofaol qilish", callback_data=f"deactivate_{user_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✅ Faol qilish", callback_data=f"activate_{user_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="list_users")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_change_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi rolini o'zgartirish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        data = update.callback_query.data
        user_id = int(data.split('_')[2])
        new_role = data.split('_')[1].upper()
        
        # Rolni yangilash
        self.db.update_user_role(user_id, new_role)
        
        # Audit log
        self.db.add_audit_log(
            user['id'], 
            'USER_ROLE_CHANGED', 
            f"Foydalanuvchi roli o'zgartirildi: ID {user_id} -> {new_role}"
        )
        
        role_name = "Admin" if new_role == UserRole.ADMIN else "Ishchi"
        
        text = f"""
✅ <b>Foydalanuvchi roli o'zgartirildi!</b>

🎭 <b>Yangi rol:</b> {role_name}
        """
        
        reply_markup = self.create_back_button("list_users")
        await self.send_message(update, context, text, reply_markup)
    
    async def handle_toggle_active(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi faolligini o'zgartirish"""
        user = self.get_user(update)
        
        if not self.check_permission(user, [UserRole.SUPER_ADMIN]):
            await self.send_message(update, context, "❌ Bu funksiya faqat Super Admin uchun!")
            return
        
        data = update.callback_query.data
        user_id = int(data.split('_')[1])
        action = data.split('_')[0]
        
        new_status = action == 'activate'
        
        # Faollikni yangilash
        query = "UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.db.execute_update(query, (new_status, user_id))
        
        # Audit log
        status_text = "faollashtirildi" if new_status else "nofaollashtirildi"
        self.db.add_audit_log(
            user['id'], 
            'USER_STATUS_CHANGED', 
            f"Foydalanuvchi {status_text}: ID {user_id}"
        )
        
        status_emoji = "✅" if new_status else "❌"
        status_text = "Faollashtirildi" if new_status else "Nofaollashtirildi"
        
        text = f"""
{status_emoji} <b>Foydalanuvchi {status_text.lower()}!</b>

{status_text}
        """
        
        reply_markup = self.create_back_button("list_users")
        await self.send_message(update, context, text, reply_markup)

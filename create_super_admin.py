#!/usr/bin/env python3
"""
To'g'ridan-to'g'ri Super Admin yaratish skripti
Bu skript orqali yangi Super Admin foydalanuvchi yaratish mumkin
"""

import sys
from database import Database
from config import UserRole

def create_super_admin():
    """Super Admin yaratish"""
    db = Database()
    
    print("👑 Super Admin yaratish skripti")
    print("=" * 40)
    
    try:
        # Ma'lumotlarni kiritish
        telegram_id = input("Telegram ID ni kiriting: ")
        full_name = input("To'liq ismni kiriting: ")
        username = input("Username ni kiriting (ixtiyoriy): ").strip() or None
        phone = input("Telefon raqamini kiriting (ixtiyoriy): ").strip() or None
        
        # Telegram ID ni tekshirish
        try:
            telegram_id = int(telegram_id)
        except ValueError:
            print("❌ Telegram ID raqam bo'lishi kerak!")
            return
        
        # Foydalanuvchi mavjudligini tekshirish
        existing_user = db.get_user_by_telegram_id(telegram_id)
        if existing_user:
            print(f"⚠️ Bu Telegram ID ({telegram_id}) allaqachon mavjud!")
            print(f"Foydalanuvchi: {existing_user['full_name']} (Rol: {existing_user['role']})")
            
            choice = input("Rolini Super Admin qilishni xohlaysizmi? (y/n): ").lower()
            if choice == 'y':
                db.update_user_role(existing_user['id'], UserRole.SUPER_ADMIN)
                print(f"✅ {existing_user['full_name']} Super Admin qilindi!")
            else:
                print("❌ Operatsiya bekor qilindi!")
            return
        
        # Yangi Super Admin yaratish
        user_id = db.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone=phone,
            role=UserRole.SUPER_ADMIN
        )
        
        print("✅ Super Admin muvaffaqiyatli yaratildi!")
        print(f"🆔 ID: {user_id}")
        print(f"👤 Ism: {full_name}")
        print(f"🆔 Telegram ID: {telegram_id}")
        print(f"📱 Username: @{username or 'Yoq'}")
        print(f"📞 Telefon: {phone or 'Yoq'}")
        print(f"👑 Rol: SUPER_ADMIN")
        
        # Audit log
        db.add_audit_log(
            user_id, 
            'SUPER_ADMIN_CREATED', 
            f"Yangi Super Admin yaratildi: {full_name}"
        )
        
        print("\n🎉 Endi botni ishga tushiring va /start komandasini bosing!")
        
    except KeyboardInterrupt:
        print("\n❌ Operatsiya bekor qilindi!")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

if __name__ == "__main__":
    create_super_admin()

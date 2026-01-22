#!/usr/bin/env python3
"""
Super Admin o'rnatish skripti
Bu skript orqali mavjud foydalanuvchini Super Admin qilish mumkin
"""

import sys
from database import Database
from config import UserRole

def setup_super_admin():
    """Super Admin o'rnatish"""
    db = Database()
    
    print("🔧 Super Admin o'rnatish skripti")
    print("=" * 40)
    
    # Barcha foydalanuvchilarni ko'rsatish
    users = db.get_all_users()
    
    if not users:
        print("❌ Hozircha foydalanuvchilar yo'q!")
        print("Avval botni ishga tushiring va /start komandasini bosing.")
        return
    
    print("📋 Mavjud foydalanuvchilar:")
    for i, user in enumerate(users, 1):
        print(f"{i}. {user['full_name']} (ID: {user['id']}, Telegram ID: {user['telegram_id']}, Rol: {user['role']})")
    
    print("\n" + "=" * 40)
    
    try:
        # Foydalanuvchi tanlash
        choice = input("Super Admin qilmoqchi bo'lgan foydalanuvchi raqamini kiriting: ")
        user_index = int(choice) - 1
        
        if 0 <= user_index < len(users):
            selected_user = users[user_index]
            
            # Rolni yangilash
            db.update_user_role(selected_user['id'], UserRole.SUPER_ADMIN)
            
            print(f"✅ {selected_user['full_name']} Super Admin qilindi!")
            print(f"🆔 Telegram ID: {selected_user['telegram_id']}")
            print(f"📱 Username: @{selected_user['username'] or 'Yoq'}")
            
            # Audit log
            db.add_audit_log(
                selected_user['id'], 
                'SUPER_ADMIN_SETUP', 
                f"Foydalanuvchi Super Admin qilindi: {selected_user['full_name']}"
            )
            
        else:
            print("❌ Noto'g'ri raqam!")
            
    except ValueError:
        print("❌ Noto'g'ri format!")
    except KeyboardInterrupt:
        print("\n❌ Operatsiya bekor qilindi!")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

if __name__ == "__main__":
    setup_super_admin()

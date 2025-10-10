import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import pytz
from config import DEFAULT_TIMEZONE

class Database:
    def __init__(self, db_path: str = "ishbot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Ma'lumotlar bazasi jadvallarini yaratish"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                phone TEXT,
                role TEXT NOT NULL CHECK(role IN ('SUPER_ADMIN', 'ADMIN', 'WORKER')),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                assigned_to INTEGER NOT NULL,
                start_at TIMESTAMP NOT NULL,
                deadline TIMESTAMP NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('PAST', 'ORTA', 'YUQORI', 'KRITIK')),
                status TEXT NOT NULL CHECK(status IN ('REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA', 'BAJARILDI', 'RAD_ETILDI', 'MUDDATI_OTGAN')),
                completed_at TIMESTAMP,
                approved_by INTEGER,
                approved_at TIMESTAMP,
                rejected_by INTEGER,
                rejected_at TIMESTAMP,
                is_penalized BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resubmit_count INTEGER DEFAULT 0,
                penalty_amount INTEGER DEFAULT 0,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (assigned_to) REFERENCES users (id),
                FOREIGN KEY (approved_by) REFERENCES users (id),
                FOREIGN KEY (rejected_by) REFERENCES users (id)
            )
        ''')
        
        # Task files jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                uploaded_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            )
        ''')
        
        # Task comments jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (author_id) REFERENCES users (id)
            )
        ''')
        
        # Audit log jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Organization settings jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS org_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_name TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Tashkent',
                penalty_amount INTEGER DEFAULT 1000000,
                work_hours_start INTEGER DEFAULT 9,
                work_hours_end INTEGER DEFAULT 18,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Task deadline extensions jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_deadline_extensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                extended_by INTEGER NOT NULL,
                old_deadline TIMESTAMP NOT NULL,
                new_deadline TIMESTAMP NOT NULL,
                extension_hours INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (extended_by) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Ma'lumotlar bazasi ulanishini olish"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Sorovni bajarish va natijalarni qaytarish"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Yangilash/ochirish/joylashtirish so'rovini bajarish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Telegram ID bo'yicha foydalanuvchini topish"""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        results = self.execute_query(query, (telegram_id,))
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Database ID bo'yicha foydalanuvchini topish"""
        query = "SELECT * FROM users WHERE id = ?"
        results = self.execute_query(query, (user_id,))
        return results[0] if results else None
    
    def create_user(self, telegram_id: int, full_name: str, username: str = None, 
                   phone: str = None, role: str = 'WORKER') -> int:
        """Yangi foydalanuvchi yaratish"""
        query = """
            INSERT INTO users (telegram_id, full_name, username, phone, role)
            VALUES (?, ?, ?, ?, ?)
        """
        user_id = self.execute_update(query, (telegram_id, full_name, username, phone, role))
        
        # Agar Super Admin ID belgilangan bo'lsa va bu foydalanuvchi Super Admin bo'lsa
        from config import SUPER_ADMIN_TELEGRAM_ID
        if SUPER_ADMIN_TELEGRAM_ID and str(telegram_id) == str(SUPER_ADMIN_TELEGRAM_ID):
            self.update_user_role(user_id, 'SUPER_ADMIN')
            self.add_audit_log(user_id, 'AUTO_SUPER_ADMIN', f"Avtomatik Super Admin yaratildi: {full_name}")
        
        return user_id
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Foydalanuvchi rolini yangilash"""
        query = "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (new_role, user_id))
        return True
    
    def update_user_full_name(self, user_id: int, full_name: str) -> bool:
        """Foydalanuvchi ism familiyasini yangilash"""
        query = "UPDATE users SET full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (full_name, user_id))
        return True
    
    def update_user_phone(self, user_id: int, phone: str) -> bool:
        """Foydalanuvchi telefon raqamini yangilash"""
        query = "UPDATE users SET phone = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (phone, user_id))
        return True
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Barcha foydalanuvchilarni olish"""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        return self.execute_query(query)
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """Faol foydalanuvchilarni olish"""
        query = "SELECT * FROM users WHERE is_active = 1 ORDER BY full_name"
        return self.execute_query(query)
    
    def get_admins(self) -> List[Dict[str, Any]]:
        """Admin va Super Admin larni olish"""
        query = "SELECT * FROM users WHERE role IN ('ADMIN', 'SUPER_ADMIN') AND is_active = 1"
        return self.execute_query(query)
    
    def get_users_by_role(self, roles: List[str]) -> List[Dict[str, Any]]:
        """Rol bo'yicha foydalanuvchilarni olish"""
        placeholders = ','.join(['?' for _ in roles])
        query = f"SELECT * FROM users WHERE role IN ({placeholders}) AND is_active = 1"
        return self.execute_query(query, tuple(roles))
    
    def create_task(self, task_id: str, title: str, description: str, created_by: int,
                   assigned_to: int, start_at: str, deadline: str, priority: str) -> int:
        """Yangi vazifa yaratish"""
        query = """
            INSERT INTO tasks (id, title, description, created_by, assigned_to, 
                             start_at, deadline, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'REJALASHTIRILGAN')
        """
        return self.execute_update(query, (task_id, title, description, created_by, 
                                         assigned_to, start_at, deadline, priority))
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Vazifa ID bo'yicha topish"""
        query = """
            SELECT t.*, u.full_name as creator_name 
            FROM tasks t 
            JOIN users u ON t.created_by = u.id 
            WHERE t.id = ?
        """
        results = self.execute_query(query, (task_id,))
        return results[0] if results else None
    
    def get_user_tasks(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Foydalanuvchiga biriktirilgan vazifalarni olish"""
        if status:
            query = """
                SELECT t.*, u.full_name as creator_name 
                FROM tasks t 
                JOIN users u ON t.created_by = u.id 
                WHERE t.assigned_to = ? AND t.status = ?
                ORDER BY t.created_at DESC
            """
            return self.execute_query(query, (user_id, status))
        else:
            query = """
                SELECT t.*, u.full_name as creator_name 
                FROM tasks t 
                JOIN users u ON t.created_by = u.id 
                WHERE t.assigned_to = ?
                ORDER BY t.created_at DESC
            """
            return self.execute_query(query, (user_id,))
    
    def get_user_tasks_by_status(self, user_id: int, statuses: List[str]) -> List[Dict[str, Any]]:
        """Foydalanuvchiga biriktirilgan vazifalarni status bo'yicha olish"""
        placeholders = ','.join(['?' for _ in statuses])
        query = f"""
            SELECT t.*, u1.full_name as creator_name, u2.full_name as rejector_name
            FROM tasks t 
            JOIN users u1 ON t.created_by = u1.id 
            LEFT JOIN users u2 ON t.rejected_by = u2.id
            WHERE t.assigned_to = ? AND t.status IN ({placeholders})
            ORDER BY t.created_at DESC
        """
        return self.execute_query(query, (user_id, *statuses))
    
    def update_task_status(self, task_id: str, status: str, approved_by: int = None, rejected_by: int = None) -> bool:
        """Vazifa statusini yangilash"""
        if status == 'RAD_ETILDI':
            query = """
                UPDATE tasks 
                SET status = ?, rejected_by = ?, rejected_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.execute_update(query, (status, rejected_by, task_id))
        else:
            query = "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.execute_update(query, (status, task_id))
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """Vazifani tugatish (ishchi tomonidan)"""
        query = """
            UPDATE tasks 
            SET status = 'TASDIQLASH_KUTILMOQDA', completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        self.execute_update(query, (task_id,))
        return True
    
    def approve_task(self, task_id: str, approved_by: int) -> bool:
        """Vazifani tasdiqlash (admin tomonidan)"""
        query = """
            UPDATE tasks 
            SET status = 'BAJARILDI', approved_by = ?, approved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        self.execute_update(query, (approved_by, task_id))
        return True
    
    def update_task_deadline(self, task_id: str, new_deadline: str) -> bool:
        """Vazifa deadline'ini yangilash"""
        query = "UPDATE tasks SET deadline = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (new_deadline, task_id))
        return True
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Muddati o'tgan vazifalarni olish"""
        query = """
            SELECT t.*, u.telegram_id, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.deadline < datetime('now') AND t.status NOT IN ('BAJARILDI', 'RAD_ETILDI')
        """
        return self.execute_query(query)
    
    def add_audit_log(self, user_id: int, action: str, details: str = None) -> int:
        """Audit logga yozish"""
        query = "INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)"
        return self.execute_update(query, (user_id, action, details))
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Audit loglarni olish"""
        query = """
            SELECT al.*, u.full_name, u.role 
            FROM audit_log al 
            JOIN users u ON al.user_id = u.id 
            ORDER BY al.created_at DESC 
            LIMIT ?
        """
        return self.execute_query(query, (limit,))
    
    def get_org_settings(self) -> Optional[Dict[str, Any]]:
        """Tashkilot sozlamalarini olish"""
        query = "SELECT * FROM org_settings ORDER BY id DESC LIMIT 1"
        results = self.execute_query(query)
        return results[0] if results else None
    
    def create_org_settings(self, org_name: str) -> int:
        """Tashkilot sozlamalarini yaratish"""
        query = """
            INSERT INTO org_settings (org_name) VALUES (?)
        """
        return self.execute_update(query, (org_name,))
    
    def get_task_resubmit_count(self, task_id: str) -> int:
        """Vazifaning qayta yuborilish sonini olish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT resubmit_count FROM tasks WHERE id = ?', (task_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def increment_resubmit_count(self, task_id: str) -> int:
        """Vazifaning qayta yuborilish sonini oshirish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET resubmit_count = resubmit_count + 1 WHERE id = ?', (task_id,))
        cursor.execute('SELECT resubmit_count FROM tasks WHERE id = ?', (task_id,))
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        return result[0] if result else 0
    
    def apply_penalty(self, task_id: str, penalty_amount: int = 1000000):
        """Vazifaga shtraf qo'llash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tasks 
            SET penalty_amount = ?, is_penalized = 1 
            WHERE id = ?
        ''', (penalty_amount, task_id))
        conn.commit()
        conn.close()
    
    def can_resubmit_task(self, task_id: str) -> bool:
        """Vazifani qayta yuborish mumkinligini tekshirish"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT resubmit_count, is_penalized FROM tasks WHERE id = ?', (task_id,))
        result = cursor.fetchone()
        conn.close()
        if not result:
            return False
        
        resubmit_count, is_penalized = result
        return resubmit_count < 3 and not is_penalized
    
    def add_deadline_extension(self, task_id: str, extended_by: int, old_deadline: str, 
                              new_deadline: str, extension_hours: int, reason: str = None) -> int:
        """Deadline uzaytirish tarixini saqlash"""
        query = """
            INSERT INTO task_deadline_extensions 
            (task_id, extended_by, old_deadline, new_deadline, extension_hours, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (task_id, extended_by, old_deadline, new_deadline, extension_hours, reason))
    
    def get_task_deadline_extensions(self, task_id: str) -> List[Dict[str, Any]]:
        """Vazifaning deadline uzaytirish tarixini olish"""
        query = """
            SELECT tde.*, u.full_name as extended_by_name
            FROM task_deadline_extensions tde
            JOIN users u ON tde.extended_by = u.id
            WHERE tde.task_id = ?
            ORDER BY tde.created_at DESC
        """
        return self.execute_query(query, (task_id,))

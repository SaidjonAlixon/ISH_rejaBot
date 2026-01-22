import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from urllib.parse import urlparse
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import pytz
from config import DEFAULT_TIMEZONE, DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        
        # Connection pool yaratish
        try:
            # URL ni parse qilish
            parsed = urlparse(self.database_url)
            self.db_config = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 5432,
                'database': parsed.path[1:] if parsed.path else 'ishbot',  # /ishbot -> ishbot
                'user': parsed.username or 'postgres',
                'password': parsed.password or 'postgres'
            }
            
            # Connection pool yaratish (min 1, max 5 connection)
            self.pool = SimpleConnectionPool(1, 5, **self.db_config)
            
            if self.pool:
                logger.info(f"PostgreSQL connection pool yaratildi: {self.db_config['database']}")
            else:
                raise Exception("Connection pool yaratib bo'lmadi")
                
        except Exception as e:
            logger.error(f"Database connection xatosi: {e}")
            raise
        
        # Database mavjudligini tekshirish va jadvallarni yaratish
        self.init_database()
    
    def get_connection(self):
        """Ma'lumotlar bazasi ulanishini olish"""
        try:
            return self.pool.getconn()
        except Exception as e:
            logger.error(f"Connection olishda xatolik: {e}")
            # Qayta urinish
            self.pool = SimpleConnectionPool(1, 5, **self.db_config)
            return self.pool.getconn()
    
    def return_connection(self, conn):
        """Connectionni pool ga qaytarish"""
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Connection qaytarishda xatolik: {e}")
    
    def init_database(self):
        """Ma'lumotlar bazasi jadvallarini yaratish"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Users jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    username VARCHAR(255),
                    phone VARCHAR(50),
                    role VARCHAR(20) NOT NULL CHECK(role IN ('SUPER_ADMIN', 'ADMIN', 'WORKER')),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tasks jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(255) PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    created_by INTEGER NOT NULL,
                    assigned_to INTEGER NOT NULL,
                    start_at TIMESTAMP NOT NULL,
                    deadline TIMESTAMP NOT NULL,
                    priority VARCHAR(20) NOT NULL CHECK(priority IN ('PAST', 'ORTA', 'YUQORI', 'KRITIK')),
                    status VARCHAR(30) NOT NULL CHECK(status IN ('REJALASHTIRILGAN', 'JARAYONDA', 'TASDIQLASH_KUTILMOQDA', 'BAJARILDI', 'RAD_ETILDI', 'MUDDATI_OTGAN')),
                    completed_at TIMESTAMP,
                    approved_by INTEGER,
                    approved_at TIMESTAMP,
                    rejected_by INTEGER,
                    rejected_at TIMESTAMP,
                    is_penalized BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resubmit_count INTEGER DEFAULT 0,
                    penalty_amount INTEGER DEFAULT 0,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE SET NULL,
                    FOREIGN KEY (rejected_by) REFERENCES users (id) ON DELETE SET NULL
                )
            ''')
            
            # Task files jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_files (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) NOT NULL,
                    file_id VARCHAR(255) NOT NULL,
                    file_name VARCHAR(500) NOT NULL,
                    uploaded_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Task comments jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_comments (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) NOT NULL,
                    author_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Audit log jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Organization settings jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS org_settings (
                    id SERIAL PRIMARY KEY,
                    org_name VARCHAR(255) NOT NULL,
                    timezone VARCHAR(50) DEFAULT 'Asia/Tashkent',
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
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) NOT NULL,
                    extended_by INTEGER NOT NULL,
                    old_deadline TIMESTAMP NOT NULL,
                    new_deadline TIMESTAMP NOT NULL,
                    extension_hours INTEGER NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (extended_by) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            logger.info("Database jadvallari yaratildi yoki mavjud")
            
            # Org_settings jadvaliga reminder_interval_minutes qo'shish (agar mavjud bo'lmasa)
            try:
                cursor.execute("""
                    ALTER TABLE org_settings 
                    ADD COLUMN IF NOT EXISTS reminder_interval_minutes INTEGER DEFAULT 180
                """)
                conn.commit()
                logger.info("reminder_interval_minutes ustuni qo'shildi yoki mavjud")
            except Exception as e:
                logger.warning(f"reminder_interval_minutes ustuni qo'shishda xatolik (ehtimol allaqachon mavjud): {e}")
                conn.rollback()
            
            # Mavjud foydalanuvchilar sonini tekshirish
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'SUPER_ADMIN'")
            admin_count = cursor.fetchone()[0]
            logger.info(f"Database contains {user_count} users, {admin_count} super admins")
            
        except Exception as e:
            logger.error(f"Database initialization xatosi: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Sorovni bajarish va natijalarni qaytarish"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # PostgreSQL placeholder ? o'rniga %s
            query = query.replace('?', '%s')
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logger.error(f"Query execution xatosi: {e}, Query: {query[:100]}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Yangilash/ochirish/joylashtirish so'rovini bajarish"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # PostgreSQL placeholder ? o'rniga %s
            query = query.replace('?', '%s')
            cursor.execute(query, params)
            conn.commit()
            # PostgreSQL da RETURNING ishlatish yoki lastrowid
            if 'RETURNING' in query.upper():
                last_id = cursor.fetchone()[0]
            else:
                last_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else 0
            return last_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Update execution xatosi: {e}, Query: {query[:100]}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Telegram ID bo'yicha foydalanuvchini topish"""
        query = "SELECT * FROM users WHERE telegram_id = %s"
        results = self.execute_query(query, (telegram_id,))
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Database ID bo'yicha foydalanuvchini topish"""
        query = "SELECT * FROM users WHERE id = %s"
        results = self.execute_query(query, (user_id,))
        return results[0] if results else None
    
    def create_user(self, telegram_id: int, full_name: str, username: str = None, 
                   phone: str = None, role: str = 'WORKER') -> int:
        """Yangi foydalanuvchi yaratish"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = """
                INSERT INTO users (telegram_id, full_name, username, phone, role)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (telegram_id, full_name, username, phone, role))
            result = cursor.fetchone()
            user_id = result['id'] if result else None
            conn.commit()
            
            if not user_id:
                raise Exception("Foydalanuvchi yaratib bo'lmadi")
            
            # Agar Super Admin ID belgilangan bo'lsa va bu foydalanuvchi hali SUPER_ADMIN emas bo'lsa
            from config import SUPER_ADMIN_TELEGRAM_IDS
            if SUPER_ADMIN_TELEGRAM_IDS and telegram_id in SUPER_ADMIN_TELEGRAM_IDS and role != 'SUPER_ADMIN':
                self.update_user_role(user_id, 'SUPER_ADMIN')
                self.add_audit_log(user_id, 'AUTO_SUPER_ADMIN', f"Avtomatik Super Admin yaratildi: {full_name}")
            
            return user_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Foydalanuvchi yaratishda xatolik: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Foydalanuvchi rolini yangilash"""
        query = "UPDATE users SET role = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        self.execute_update(query, (new_role, user_id))
        return True
    
    def update_user_full_name(self, user_id: int, full_name: str) -> bool:
        """Foydalanuvchi ism familiyasini yangilash"""
        query = "UPDATE users SET full_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        self.execute_update(query, (full_name, user_id))
        return True
    
    def update_user_phone(self, user_id: int, phone: str) -> bool:
        """Foydalanuvchi telefon raqamini yangilash"""
        query = "UPDATE users SET phone = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        self.execute_update(query, (phone, user_id))
        return True
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Barcha foydalanuvchilarni olish"""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        return self.execute_query(query)
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """Faol foydalanuvchilarni olish"""
        query = "SELECT * FROM users WHERE is_active = TRUE ORDER BY full_name"
        return self.execute_query(query)
    
    def get_admins(self) -> List[Dict[str, Any]]:
        """Admin va Super Admin larni olish"""
        query = "SELECT * FROM users WHERE role IN ('ADMIN', 'SUPER_ADMIN') AND is_active = TRUE"
        return self.execute_query(query)
    
    def get_users_by_role(self, roles: List[str]) -> List[Dict[str, Any]]:
        """Rol bo'yicha foydalanuvchilarni olish"""
        placeholders = ','.join(['%s' for _ in roles])
        query = f"SELECT * FROM users WHERE role IN ({placeholders}) AND is_active = TRUE"
        return self.execute_query(query, tuple(roles))
    
    def create_task(self, task_id: str, title: str, description: str, created_by: int,
                   assigned_to: int, start_at: str, deadline: str, priority: str) -> int:
        """Yangi vazifa yaratish"""
        query = """
            INSERT INTO tasks (id, title, description, created_by, assigned_to, 
                             start_at, deadline, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'REJALASHTIRILGAN')
        """
        return self.execute_update(query, (task_id, title, description, created_by, 
                                         assigned_to, start_at, deadline, priority))
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Vazifa ID bo'yicha topish"""
        query = """
            SELECT t.*, u.full_name as creator_name 
            FROM tasks t 
            JOIN users u ON t.created_by = u.id 
            WHERE t.id = %s
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
                WHERE t.assigned_to = %s AND t.status = %s
                ORDER BY t.created_at DESC
            """
            return self.execute_query(query, (user_id, status))
        else:
            query = """
                SELECT t.*, u.full_name as creator_name 
                FROM tasks t 
                JOIN users u ON t.created_by = u.id 
                WHERE t.assigned_to = %s
                ORDER BY t.created_at DESC
            """
            return self.execute_query(query, (user_id,))
    
    def get_user_tasks_by_status(self, user_id: int, statuses: List[str]) -> List[Dict[str, Any]]:
        """Foydalanuvchiga biriktirilgan vazifalarni status bo'yicha olish"""
        # Agar statuses bo'sh bo'lsa, barcha vazifalarni qaytarish
        if not statuses:
            query = """
                SELECT t.*, u1.full_name as creator_name, u2.full_name as rejector_name
                FROM tasks t 
                JOIN users u1 ON t.created_by = u1.id 
                LEFT JOIN users u2 ON t.rejected_by = u2.id
                WHERE t.assigned_to = %s
                ORDER BY t.created_at DESC
            """
            return self.execute_query(query, (user_id,))
        
        placeholders = ','.join(['%s' for _ in statuses])
        query = f"""
            SELECT t.*, u1.full_name as creator_name, u2.full_name as rejector_name
            FROM tasks t 
            JOIN users u1 ON t.created_by = u1.id 
            LEFT JOIN users u2 ON t.rejected_by = u2.id
            WHERE t.assigned_to = %s AND t.status IN ({placeholders})
            ORDER BY t.created_at DESC
        """
        return self.execute_query(query, (user_id, *statuses))
    
    def update_task_status(self, task_id: str, status: str, approved_by: int = None, rejected_by: int = None) -> bool:
        """Vazifa statusini yangilash"""
        if status == 'RAD_ETILDI':
            query = """
                UPDATE tasks 
                SET status = %s, rejected_by = %s, rejected_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.execute_update(query, (status, rejected_by, task_id))
        else:
            query = "UPDATE tasks SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            self.execute_update(query, (status, task_id))
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """Vazifani tugatish (ishchi tomonidan)"""
        query = """
            UPDATE tasks 
            SET status = 'TASDIQLASH_KUTILMOQDA', completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute_update(query, (task_id,))
        return True
    
    def approve_task(self, task_id: str, approved_by: int) -> bool:
        """Vazifani tasdiqlash (admin tomonidan)"""
        query = """
            UPDATE tasks 
            SET status = 'BAJARILDI', approved_by = %s, approved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute_update(query, (approved_by, task_id))
        return True
    
    def update_task_deadline(self, task_id: str, new_deadline: str) -> bool:
        """Vazifa deadline'ini yangilash"""
        query = "UPDATE tasks SET deadline = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        self.execute_update(query, (new_deadline, task_id))
        return True
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Muddati o'tgan vazifalarni olish"""
        query = """
            SELECT t.*, u.telegram_id, u.full_name as assigned_name 
            FROM tasks t 
            JOIN users u ON t.assigned_to = u.id 
            WHERE t.deadline < NOW() AND t.status NOT IN ('BAJARILDI', 'RAD_ETILDI')
        """
        return self.execute_query(query)
    
    def add_audit_log(self, user_id: int, action: str, details: str = None) -> int:
        """Audit logga yozish"""
        query = "INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s) RETURNING id"
        result = self.execute_query(query, (user_id, action, details))
        return result[0]['id'] if result else 0
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Audit loglarni olish"""
        query = """
            SELECT al.*, u.full_name, u.role 
            FROM audit_log al 
            JOIN users u ON al.user_id = u.id 
            ORDER BY al.created_at DESC 
            LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def get_org_settings(self) -> Optional[Dict[str, Any]]:
        """Tashkilot sozlamalarini olish"""
        query = "SELECT * FROM org_settings ORDER BY id DESC LIMIT 1"
        results = self.execute_query(query)
        return results[0] if results else None
    
    def create_org_settings(self, org_name: str) -> int:
        """Tashkilot sozlamalarini yaratish"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = """
                INSERT INTO org_settings (org_name) VALUES (%s) RETURNING id
            """
            cursor.execute(query, (org_name,))
            result = cursor.fetchone()
            settings_id = result['id'] if result else None
            conn.commit()
            
            if not settings_id:
                raise Exception("Tashkilot sozlamalari yaratib bo'lmadi")
            
            return settings_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Tashkilot sozlamalari yaratishda xatolik: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_task_resubmit_count(self, task_id: str) -> int:
        """Vazifaning qayta yuborilish sonini olish"""
        query = 'SELECT resubmit_count FROM tasks WHERE id = %s'
        results = self.execute_query(query, (task_id,))
        return results[0]['resubmit_count'] if results else 0
    
    def increment_resubmit_count(self, task_id: str) -> int:
        """Vazifaning qayta yuborilish sonini oshirish"""
        query = '''
            UPDATE tasks SET resubmit_count = resubmit_count + 1 
            WHERE id = %s
            RETURNING resubmit_count
        '''
        result = self.execute_query(query, (task_id,))
        return result[0]['resubmit_count'] if result else 0
    
    def apply_penalty(self, task_id: str, penalty_amount: int = 1000000):
        """Vazifaga shtraf qo'llash"""
        query = '''
            UPDATE tasks 
            SET penalty_amount = %s, is_penalized = TRUE 
            WHERE id = %s
        '''
        self.execute_update(query, (penalty_amount, task_id))
    
    def can_resubmit_task(self, task_id: str) -> bool:
        """Vazifani qayta yuborish mumkinligini tekshirish"""
        query = 'SELECT resubmit_count, is_penalized FROM tasks WHERE id = %s'
        results = self.execute_query(query, (task_id,))
        if not results:
            return False
        
        result = results[0]
        resubmit_count = result['resubmit_count']
        is_penalized = result['is_penalized']
        return resubmit_count < 3 and not is_penalized
    
    def add_deadline_extension(self, task_id: str, extended_by: int, old_deadline: str, 
                              new_deadline: str, extension_hours: int, reason: str = None) -> int:
        """Deadline uzaytirish tarixini saqlash"""
        query = """
            INSERT INTO task_deadline_extensions 
            (task_id, extended_by, old_deadline, new_deadline, extension_hours, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(query, (task_id, extended_by, old_deadline, new_deadline, extension_hours, reason))
        return result[0]['id'] if result else 0
    
    def get_task_deadline_extensions(self, task_id: str) -> List[Dict[str, Any]]:
        """Vazifaning deadline uzaytirish tarixini olish"""
        query = """
            SELECT tde.*, u.full_name as extended_by_name
            FROM task_deadline_extensions tde
            JOIN users u ON tde.extended_by = u.id
            WHERE tde.task_id = %s
            ORDER BY tde.created_at DESC
        """
        return self.execute_query(query, (task_id,))

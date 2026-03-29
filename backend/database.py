"""
Database configuration and initialization for Smart Public Complaint System
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/smartgov")

def get_db():
    """Get database connection"""
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_db()
    cursor = conn.cursor()

    # Users table (Citizens, Admins, Department Staff)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'citizen',  -- citizen | admin | staff
            department TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP WITH TIME ZONE
        )
    """)

    # Complaints table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id SERIAL PRIMARY KEY,
            complaint_number TEXT UNIQUE NOT NULL,
            citizen_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,  -- water | electricity | sanitation | infrastructure | other
            department TEXT NOT NULL,
            location TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',  -- low | medium | high | urgent
            status TEXT DEFAULT 'submitted',  -- submitted | acknowledged | in_progress | resolved | closed | rejected
            assigned_to INTEGER,
            attachment_path TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP WITH TIME ZONE,
            resolution_notes TEXT,
            FOREIGN KEY (citizen_id) REFERENCES users(id),
            FOREIGN KEY (assigned_to) REFERENCES users(id)
        )
    """)

    # Complaint timeline / audit trail
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaint_timeline (
            id SERIAL PRIMARY KEY,
            complaint_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            notes TEXT,
            updated_by INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
            FOREIGN KEY (updated_by) REFERENCES users(id)
        )
    """)

    # Ratings / feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            complaint_id INTEGER UNIQUE NOT NULL,
            citizen_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,  -- 1-5
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
            FOREIGN KEY (citizen_id) REFERENCES users(id)
        )
    """)

    # Notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            complaint_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    # Seed default admin user
    cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@smartgov.in',))
    if not cursor.fetchone():
        import hashlib
        admin_hash = hashlib.sha256("Admin@123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role, department)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("System Administrator", "admin@smartgov.in", "9000000000", admin_hash, "admin", "Administration"))

        # Seed department staff
        staff_data = [
            ("Water Dept Staff", "water@smartgov.in", "9000000001", "Staff@123", "staff", "Water Supply"),
            ("Electricity Staff", "electric@smartgov.in", "9000000002", "Staff@123", "staff", "Electricity"),
            ("Sanitation Staff", "sanitation@smartgov.in", "9000000003", "Staff@123", "staff", "Sanitation"),
            ("Infrastructure Staff", "infra@smartgov.in", "9000000004", "Staff@123", "staff", "Infrastructure"),
        ]
        for s in staff_data:
            h = hashlib.sha256(s[3].encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (full_name, email, phone, password_hash, role, department)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (s[0], s[1], s[2], h, s[4], s[5]))

        # Seed a demo citizen
        citizen_hash = hashlib.sha256("Citizen@123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
        """, ("Demo Citizen", "citizen@demo.in", "9876543210", citizen_hash, "citizen"))

        conn.commit()

    cursor.close()
    conn.close()
    print(f"[DB] Database initialized at {DB_URL}")


if __name__ == "__main__":
    init_db()

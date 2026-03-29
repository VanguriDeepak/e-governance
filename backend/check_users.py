import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/smartgov")

def check_users():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute('SELECT id, full_name, email, role, department FROM users ORDER BY id')
    for r in cur.fetchall():
        print(f"ID:{r['id']} | {r['role']:8} | {r['email']:35} | {r['department']}")
    conn.close()

if __name__ == '__main__':
    check_users()

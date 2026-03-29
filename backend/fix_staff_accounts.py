"""
Fix: Insert missing staff accounts into existing database
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/smartgov")

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

staff_to_add = [
    ("Water Dept Staff",      "water@smartgov.in",      "9000000001", "Staff@123", "staff", "Water Supply"),
    ("Electricity Staff",     "electric@smartgov.in",   "9000000002", "Staff@123", "staff", "Electricity"),
    ("Sanitation Staff",      "sanitation@smartgov.in", "9000000003", "Staff@123", "staff", "Sanitation"),
    ("Infrastructure Staff",  "infra@smartgov.in",      "9000000004", "Staff@123", "staff", "Infrastructure"),
]

inserted = 0
skipped = 0

for name, email, phone, password, role, dept in staff_to_add:
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        print(f"  SKIP (already exists): {email}")
        skipped += 1
    else:
        cur.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role, department)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, phone, hash_password(password), role, dept))
        print(f"  ADDED: {email} | dept={dept}")
        inserted += 1

conn.commit()
conn.close()

print(f"\nDone! Inserted: {inserted}, Skipped: {skipped}")
print("\nAll users now in DB:")

conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, full_name, email, role, department FROM users ORDER BY id")
for r in cur.fetchall():
    print(f"  ID:{r['id']} | {r['role']:8} | {r['email']:35} | {r['department']}")
conn.close()

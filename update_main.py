import re

with open(r'C:\Users\anand\OneDrive\Desktop\Smart Public Complaint\Smart Public Complaint\backend\main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Replace %s placeholder replacements
text = text.replace('email = ?', 'email = %s')
text = text.replace('VALUES (?, ?, ?, ?, ?, ?)', 'VALUES (%s, %s, %s, %s, %s, %s)')
text = text.replace('id = ?', 'id = %s')
text = text.replace('citizen_id = ?', 'citizen_id = %s')
text = text.replace('status = ?', 'status = %s')
text = text.replace('category = ?', 'category = %s')
text = text.replace('priority = ?', 'priority = %s')
text = text.replace('department = ?', 'department = %s')

# Replace "?, 'Complaint Submitted', 'submitted', 'Complaint registered successfully', ?"
text = text.replace(
    "VALUES (?, 'Complaint Submitted', 'submitted', 'Complaint registered successfully', ?)",
    "VALUES (%s, 'Complaint Submitted', 'submitted', 'Complaint registered successfully', %s)"
)

# Replace "VALUES (?, ?, ?)"
text = text.replace('VALUES (?, ?, ?)', 'VALUES (%s, %s, %s)')

# LIMIT ? OFFSET ? -> LIMIT %s OFFSET %s
text = text.replace('LIMIT ? OFFSET ?', 'LIMIT %s OFFSET %s')

# UPDATE complaints SET status = ?, ... -> UPDATE complaints SET status = %s, ...
text = text.replace("SET status = ?, updated_at = datetime('now'), resolved_at = datetime('now'),", "SET status = %s, updated_at = CURRENT_TIMESTAMP, resolved_at = CURRENT_TIMESTAMP,")
text = text.replace("resolution_notes = ?, assigned_to = COALESCE(?, assigned_to)", "resolution_notes = %s, assigned_to = COALESCE(%s, assigned_to)")
text = text.replace("SET status = ?, updated_at = datetime('now'),", "SET status = %s, updated_at = CURRENT_TIMESTAMP,")

text = text.replace('VALUES (?, ?, ?, ?, ?, ?)', 'VALUES (%s, %s, %s, %s, %s, %s)') # Already did, but double check
text = text.replace('VALUES (?, ?, ?, ?, ?, ?, ?, ?, \'submitted\')', 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, \'submitted\')')

# 2. Date/time string replacements
text = text.replace("last_login = datetime('now')", "last_login = CURRENT_TIMESTAMP")


# 3. Lastrowid replacements for INSERT ... RETURNING id
text = re.sub(
    r'(INSERT INTO users.*?)(\s*VALUES.*?\))',
    r'\1\2\n            RETURNING id',
    text, flags=re.DOTALL
)
text = text.replace('user_id = cursor.lastrowid', 'user_id = cursor.fetchone()["id"]')

text = re.sub(
    r'(INSERT INTO complaints.*?)(\s*VALUES.*?\))',
    r'\1\2\n            RETURNING id',
    text, flags=re.DOTALL
)
text = text.replace('complaint_id = cursor.lastrowid', 'complaint_id = cursor.fetchone()["id"]')

# 4. Feedback Upsert (INSERT OR REPLACE)
old_feedback = """            INSERT OR REPLACE INTO feedback (complaint_id, citizen_id, rating, comment)
            VALUES (?, ?, ?, ?)"""
new_feedback = """            INSERT INTO feedback (complaint_id, citizen_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (complaint_id) DO UPDATE SET
                rating = EXCLUDED.rating,
                comment = EXCLUDED.comment"""
text = text.replace(old_feedback, new_feedback)

# 5. Dashboard Dates & julianday
old_avg_time = """            SELECT AVG(
                (julianday(resolved_at) - julianday(created_at)) * 24
            ) as avg_hours
            FROM complaints WHERE resolved_at IS NOT NULL"""
new_avg_time = """            SELECT AVG(
                EXTRACT(EPOCH FROM (resolved_at::timestamp - created_at::timestamp)) / 3600
            ) as avg_hours
            FROM complaints WHERE resolved_at IS NOT NULL"""
text = text.replace(old_avg_time, new_avg_time)

old_monthly = """            SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
            FROM complaints
            WHERE created_at >= date('now', '-6 months')
            GROUP BY month ORDER BY month"""
new_monthly = """            SELECT TO_CHAR(created_at, 'YYYY-MM') as month, COUNT(*) as count
            FROM complaints
            WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY month ORDER BY month"""
text = text.replace(old_monthly, new_monthly)

text = text.replace("user_id = %s AND is_read = 0", "user_id = %s AND is_read = 0") # no change but make sure ? handles
text = text.replace("WHERE user_id = ? AND is_read = 0", "WHERE user_id = %s AND is_read = 0")
text = text.replace("WHERE id = ? AND user_id = ?", "WHERE id = %s AND user_id = %s")

text = text.replace("attachment_path = ? WHERE id = ?", "attachment_path = %s WHERE id = %s")


with open(r'C:\Users\anand\OneDrive\Desktop\Smart Public Complaint\Smart Public Complaint\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done updating main.py")

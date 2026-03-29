"""
Main FastAPI application for Smart Public Complaint & Grievance Redressal System
"""
from fastapi import FastAPI, HTTPException, Header, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import shutil
import time
from datetime import datetime

from database import get_db, init_db
from auth import (
    hash_password, verify_password, create_token,
    verify_token, generate_complaint_number
)

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Gov Complaint API",
    description="RESTful API for Smart Public Complaint & Grievance Redressal System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount static frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print("[STARTUP] Smart Gov Complaint System started!")


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str
    role: str = "citizen"  # citizen | admin | staff
    department: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ComplaintRequest(BaseModel):
    title: str
    description: str
    category: str  # water | electricity | sanitation | infrastructure | other
    department: str
    location: str
    priority: str = "medium"


class UpdateComplaintRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    assigned_to: Optional[int] = None


class FeedbackRequest(BaseModel):
    complaint_id: int
    rating: int  # 1-5
    comment: Optional[str] = None


class MarkNotificationRead(BaseModel):
    notification_id: int


# ─── Auth Helpers ─────────────────────────────────────────────────────────────
def get_current_user(authorization: str = Header(...)):
    """Extract and verify current user from Authorization header"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return payload


def require_role(roles: list, authorization: str = Header(...)):
    """Check user has required role"""
    user = get_current_user(authorization)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail=f"Access denied. Required role: {roles}")
    return user


# ─── ROUTE: Root ──────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Smart Gov Complaint API is running. Visit /api/docs for documentation."}


# ─── ROUTE: Health Check ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "Smart Public Complaint & Grievance Redressal System"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: POST /api/auth/register - User Registration
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/auth/register", tags=["Authentication"])
def register(data: RegisterRequest):
    """Register a new user (citizen/admin/staff)"""
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if data.role not in ["citizen", "admin", "staff"]:
        raise HTTPException(status_code=400, detail="Invalid role. Choose: citizen, admin, staff")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role, department)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data.full_name, data.email, data.phone,
              hash_password(data.password), data.role, data.department))
        user_id = cursor.fetchone()["id"]
        conn.commit()

        token = create_token(user_id, data.email, data.role)
        return {
            "success": True,
            "message": "Registration successful",
            "token": token,
            "user": {
                "id": user_id,
                "full_name": data.full_name,
                "email": data.email,
                "role": data.role,
                "department": data.department
            }
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: POST /api/auth/login - User Login
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/auth/login", tags=["Authentication"])
def login(data: LoginRequest):
    """Authenticate user and return JWT token"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_active = 1", (data.email,))
        user = cursor.fetchone()

        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user["id"],))
        conn.commit()

        token = create_token(user["id"], user["email"], user["role"])
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role"],
                "department": user["department"]
            }
        }
    finally:
        conn.close()


@app.get("/api/auth/me", tags=["Authentication"])
def get_me(authorization: str = Header(...)):
    """Get current authenticated user profile"""
    current_user = get_current_user(authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, phone, role, department, created_at, last_login FROM users WHERE id = %s",
                       (current_user["user_id"],))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "user": dict(user)}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: POST /api/complaints - Submit New Complaint
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/complaints", tags=["Complaints"])
def submit_complaint(data: ComplaintRequest, authorization: str = Header(...)):
    """Submit a new complaint (citizens only)"""
    current_user = get_current_user(authorization)

    valid_categories = ["water", "electricity", "sanitation", "infrastructure", "other"]
    valid_priorities = ["low", "medium", "high", "urgent"]

    if data.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Choose: {valid_categories}")
    if data.priority not in valid_priorities:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Choose: {valid_priorities}")

    complaint_number = generate_complaint_number()
    time.sleep(0.001)  # ensure uniqueness

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (complaint_number, citizen_id, title, description,
                category, department, location, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'submitted')
            RETURNING id
        """, (complaint_number, current_user["user_id"], data.title, data.description,
              data.category, data.department, data.location, data.priority))

        complaint_id = cursor.fetchone()["id"]

        # Add timeline entry
        cursor.execute("""
            INSERT INTO complaint_timeline (complaint_id, action, new_status, notes, updated_by)
            VALUES (%s, 'Complaint Submitted', 'submitted', 'Complaint registered successfully', %s)
        """, (complaint_id, current_user["user_id"]))

        # Notify admins
        cursor.execute("SELECT id FROM users WHERE role IN ('admin', 'staff') AND is_active = 1")
        admins = cursor.fetchall()
        for admin in admins:
            cursor.execute("""
                INSERT INTO notifications (user_id, complaint_id, message)
                VALUES (%s, %s, %s)
            """, (admin["id"], complaint_id,
                  f"New complaint #{complaint_number}: {data.title} received"))

        conn.commit()
        return {
            "success": True,
            "message": "Complaint submitted successfully",
            "complaint_number": complaint_number,
            "complaint_id": complaint_id
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: GET /api/complaints - List Complaints (role-filtered)
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/complaints", tags=["Complaints"])
def list_complaints(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    authorization: str = Header(...)
):
    """List complaints - citizens see own, admins/staff see all"""
    current_user = get_current_user(authorization)
    offset = (page - 1) * limit

    conn = get_db()
    try:
        cursor = conn.cursor()
        where_clauses = []
        params = []

        # Citizens only see their own complaints
        if current_user["role"] == "citizen":
            where_clauses.append("c.citizen_id = %s")
            params.append(current_user["user_id"])

        if status:
            where_clauses.append("c.status = %s")
            params.append(status)
        if category:
            where_clauses.append("c.category = %s")
            params.append(category)
        if priority:
            where_clauses.append("c.priority = %s")
            params.append(priority)
        if department:
            where_clauses.append("c.department = %s")
            params.append(department)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        count_query = f"SELECT COUNT(*) as total FROM complaints c {where_sql}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]

        query = f"""
            SELECT c.*,
                   u.full_name as citizen_name,
                   u.email as citizen_email,
                   s.full_name as assigned_name
            FROM complaints c
            LEFT JOIN users u ON c.citizen_id = u.id
            LEFT JOIN users s ON c.assigned_to = s.id
            {where_sql}
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [limit, offset])
        complaints = [dict(row) for row in cursor.fetchall()]

        return {
            "success": True,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "complaints": complaints
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5: GET /api/complaints/{id} - Get Single Complaint with Timeline
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/complaints/{complaint_id}", tags=["Complaints"])
def get_complaint(complaint_id: int, authorization: str = Header(...)):
    """Get complaint details with full timeline"""
    current_user = get_current_user(authorization)

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*,
                   u.full_name as citizen_name, u.email as citizen_email, u.phone as citizen_phone,
                   s.full_name as assigned_name, s.email as assigned_email
            FROM complaints c
            LEFT JOIN users u ON c.citizen_id = u.id
            LEFT JOIN users s ON c.assigned_to = s.id
            WHERE c.id = %s
        """, (complaint_id,))
        complaint = cursor.fetchone()

        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        # Citizens can only view their own complaints
        if current_user["role"] == "citizen" and complaint["citizen_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get timeline
        cursor.execute("""
            SELECT t.*, u.full_name as updated_by_name
            FROM complaint_timeline t
            LEFT JOIN users u ON t.updated_by = u.id
            WHERE t.complaint_id = %s
            ORDER BY t.created_at ASC
        """, (complaint_id,))
        timeline = [dict(row) for row in cursor.fetchall()]

        # Get feedback
        cursor.execute("SELECT * FROM feedback WHERE complaint_id = %s", (complaint_id,))
        feedback = cursor.fetchone()

        return {
            "success": True,
            "complaint": dict(complaint),
            "timeline": timeline,
            "feedback": dict(feedback) if feedback else None
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 6: PUT /api/complaints/{id}/status - Update Complaint Status
# ═══════════════════════════════════════════════════════════════════════════════
@app.put("/api/complaints/{complaint_id}/status", tags=["Complaints"])
def update_complaint_status(
    complaint_id: int,
    data: UpdateComplaintRequest,
    authorization: str = Header(...)
):
    """Update complaint status (admin/staff only)"""
    current_user = require_role(["admin", "staff"], authorization)

    valid_statuses = ["submitted", "acknowledged", "in_progress", "resolved", "closed", "rejected"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose: {valid_statuses}")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = %s", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        old_status = complaint["status"]
        resolved_at = "datetime('now')" if data.status == "resolved" else None

        if resolved_at:
            cursor.execute("""
                UPDATE complaints
                SET status = %s, updated_at = datetime('now'), resolved_at = datetime('now'),
                    resolution_notes = %s, assigned_to = COALESCE(%s, assigned_to)
                WHERE id = %s
            """, (data.status, data.notes, data.assigned_to, complaint_id))
        else:
            cursor.execute("""
                UPDATE complaints
                SET status = %s, updated_at = datetime('now'),
                    resolution_notes = %s, assigned_to = COALESCE(%s, assigned_to)
                WHERE id = %s
            """, (data.status, data.notes, data.assigned_to, complaint_id))

        # Add timeline
        cursor.execute("""
            INSERT INTO complaint_timeline (complaint_id, action, old_status, new_status, notes, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (complaint_id, f"Status updated to {data.status}",
              old_status, data.status, data.notes, current_user["user_id"]))

        # Notify citizen
        cursor.execute("""
            INSERT INTO notifications (user_id, complaint_id, message)
            VALUES (%s, %s, %s)
        """, (complaint["citizen_id"], complaint_id,
              f"Your complaint #{complaint['complaint_number']} status updated to: {data.status.upper()}"))

        conn.commit()
        return {"success": True, "message": f"Complaint status updated to {data.status}"}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 7: GET /api/analytics/dashboard - Analytics Dashboard Data
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/analytics/dashboard", tags=["Analytics"])
def get_analytics_dashboard(authorization: str = Header(...)):
    """Get comprehensive analytics data for dashboard"""
    current_user = require_role(["admin", "staff"], authorization)

    conn = get_db()
    try:
        cursor = conn.cursor()

        # Total complaints by status
        cursor.execute("""
            SELECT status, COUNT(*) as count FROM complaints GROUP BY status
        """)
        status_stats = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Total complaints by category
        cursor.execute("""
            SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC
        """)
        category_stats = [dict(row) for row in cursor.fetchall()]

        # Total complaints by department
        cursor.execute("""
            SELECT department, COUNT(*) as total,
                   SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN status NOT IN ('resolved', 'closed') THEN 1 ELSE 0 END) as pending
            FROM complaints GROUP BY department
        """)
        department_stats = [dict(row) for row in cursor.fetchall()]

        # Average resolution time (in hours)
        cursor.execute("""
            SELECT AVG(
                EXTRACT(EPOCH FROM (resolved_at::timestamp - created_at::timestamp)) / 3600
            ) as avg_hours
            FROM complaints WHERE resolved_at IS NOT NULL
        """)
        avg_resolution = cursor.fetchone()["avg_hours"]

        # Complaints by priority
        cursor.execute("""
            SELECT priority, COUNT(*) as count FROM complaints GROUP BY priority
        """)
        priority_stats = {row["priority"]: row["count"] for row in cursor.fetchall()}

        # Monthly trend (last 6 months)
        cursor.execute("""
            SELECT TO_CHAR(created_at, 'YYYY-MM') as month, COUNT(*) as count
            FROM complaints
            WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY month ORDER BY month
        """)
        monthly_trend = [dict(row) for row in cursor.fetchall()]

        # Total registered users
        cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        user_stats = {row["role"]: row["count"] for row in cursor.fetchall()}

        # Top performing staff
        cursor.execute("""
            SELECT u.full_name, u.department,
                   COUNT(c.id) as resolved_count
            FROM users u
            LEFT JOIN complaints c ON c.assigned_to = u.id AND c.status = 'resolved'
            WHERE u.role = 'staff'
            GROUP BY u.id ORDER BY resolved_count DESC LIMIT 5
        """)
        top_staff = [dict(row) for row in cursor.fetchall()]

        # Recent complaints (last 5)
        cursor.execute("""
            SELECT c.*, u.full_name as citizen_name
            FROM complaints c LEFT JOIN users u ON c.citizen_id = u.id
            ORDER BY c.created_at DESC LIMIT 5
        """)
        recent_complaints = [dict(row) for row in cursor.fetchall()]

        total_complaints = sum(status_stats.values())
        resolved = status_stats.get("resolved", 0) + status_stats.get("closed", 0)
        resolution_rate = round((resolved / total_complaints * 100), 1) if total_complaints > 0 else 0

        return {
            "success": True,
            "summary": {
                "total_complaints": total_complaints,
                "resolved": resolved,
                "pending": status_stats.get("submitted", 0) + status_stats.get("acknowledged", 0),
                "in_progress": status_stats.get("in_progress", 0),
                "resolution_rate": resolution_rate,
                "avg_resolution_hours": round(avg_resolution, 1) if avg_resolution else 0,
                "total_citizens": user_stats.get("citizen", 0),
                "total_staff": user_stats.get("staff", 0)
            },
            "status_stats": status_stats,
            "category_stats": category_stats,
            "department_stats": department_stats,
            "priority_stats": priority_stats,
            "monthly_trend": monthly_trend,
            "top_staff": top_staff,
            "recent_complaints": recent_complaints
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 8: POST /api/complaints/{id}/feedback - Submit Feedback
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/complaints/{complaint_id}/feedback", tags=["Complaints"])
def submit_feedback(complaint_id: int, data: FeedbackRequest, authorization: str = Header(...)):
    """Submit feedback/rating for a resolved complaint"""
    current_user = get_current_user(authorization)

    if not (1 <= data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = %s", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        if complaint["citizen_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        if complaint["status"] not in ["resolved", "closed"]:
            raise HTTPException(status_code=400, detail="Can only rate resolved/closed complaints")

        cursor.execute("""
            INSERT INTO feedback (complaint_id, citizen_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (complaint_id) DO UPDATE SET
                rating = EXCLUDED.rating,
                comment = EXCLUDED.comment
        """, (complaint_id, current_user["user_id"], data.rating, data.comment))
        conn.commit()
        return {"success": True, "message": "Feedback submitted successfully"}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 9: GET /api/notifications - Get User Notifications
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/notifications", tags=["Notifications"])
def get_notifications(authorization: str = Header(...)):
    """Get notifications for current user"""
    current_user = get_current_user(authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.*, c.complaint_number
            FROM notifications n
            LEFT JOIN complaints c ON n.complaint_id = c.id
            WHERE n.user_id = %s
            ORDER BY n.created_at DESC LIMIT 20
        """, (current_user["user_id"],))
        notifications = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as unread FROM notifications WHERE user_id = %s AND is_read = 0",
                       (current_user["user_id"],))
        unread_count = cursor.fetchone()["unread"]

        return {"success": True, "notifications": notifications, "unread_count": unread_count}
    finally:
        conn.close()


@app.put("/api/notifications/{notification_id}/read", tags=["Notifications"])
def mark_notification_read(notification_id: int, authorization: str = Header(...)):
    """Mark a notification as read"""
    current_user = get_current_user(authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
                       (notification_id, current_user["user_id"]))
        conn.commit()
        return {"success": True, "message": "Notification marked as read"}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 10: GET /api/admin/users - Admin: List All Users
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/admin/users", tags=["Admin"])
def list_users(authorization: str = Header(...)):
    """List all users (admin only)"""
    require_role(["admin"], authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, email, phone, role, department, is_active, created_at, last_login
            FROM users ORDER BY created_at DESC
        """)
        users = [dict(row) for row in cursor.fetchall()]
        return {"success": True, "users": users, "total": len(users)}
    finally:
        conn.close()


@app.get("/api/admin/staff", tags=["Admin"])
def list_staff(authorization: str = Header(...)):
    """List all staff members"""
    require_role(["admin", "staff"], authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, email, role, department FROM users
            WHERE role IN ('admin', 'staff') AND is_active = 1
        """)
        staff = [dict(row) for row in cursor.fetchall()]
        return {"success": True, "staff": staff}
    finally:
        conn.close()


# File upload endpoint
@app.post("/api/complaints/{complaint_id}/upload", tags=["Complaints"])
async def upload_attachment(
    complaint_id: int,
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    """Upload attachment for a complaint"""
    current_user = get_current_user(authorization)
    allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only images and PDFs are allowed")

    filename = f"complaint_{complaint_id}_{int(time.time())}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE complaints SET attachment_path = %s WHERE id = %s",
                       (filename, complaint_id))
        conn.commit()
    finally:
        conn.close()

    return {"success": True, "filename": filename, "message": "File uploaded successfully"}



# ─── DELETE Complaint ─────────────────────────────────────────────────────────
@app.delete("/api/complaints/{complaint_id}", tags=["Complaints"])
def delete_complaint(complaint_id: int, authorization: str = Header(...)):
    """Delete a complaint. Rules:
    - Citizens: can delete own complaints if status is 'submitted'.
    - Staff: can delete complaints in their department.
    - Admin: can delete any complaint.
    """
    current_user = get_current_user(authorization)
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Fetch the complaint
        cursor.execute("""
            SELECT id, citizen_id, department, status FROM complaints WHERE id = %s
        """, (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")

        role = current_user["role"]
        user_id = current_user["user_id"]

        if role == "citizen":
            if complaint["citizen_id"] != user_id:
                raise HTTPException(status_code=403, detail="You can only delete your own complaints")
            if complaint["status"] not in ("submitted", "acknowledged"):
                raise HTTPException(
                    status_code=403,
                    detail="You can only delete complaints that are still Submitted or Acknowledged"
                )
        elif role == "staff":
            dept = current_user.get("department")
            if dept and complaint["department"] != dept:
                raise HTTPException(status_code=403, detail="You can only delete complaints from your department")
        # admin: no restrictions

        # Cascade delete: timeline, notifications, then complaint
        cursor.execute("DELETE FROM complaint_timeline WHERE complaint_id = %s", (complaint_id,))
        cursor.execute("DELETE FROM notifications WHERE complaint_id = %s", (complaint_id,))
        cursor.execute("DELETE FROM complaints WHERE id = %s", (complaint_id,))
        conn.commit()
        return {"success": True, "message": "Complaint deleted successfully"}
    finally:
        conn.close()


# ─── Catch-all: Serve frontend files at root level ────────────────────────────
# This allows relative links in index.html (e.g. href="login.html") to work
# when index.html is served at "/" instead of "/static/index.html"
@app.get("/{filepath:path}", include_in_schema=False)
def serve_frontend(filepath: str):
    """Serve frontend files from root path (catch-all)"""
    file_path = os.path.join(FRONTEND_DIR, filepath)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

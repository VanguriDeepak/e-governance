# 🏛️ SmartGov — Smart Public Complaint & Grievance Redressal System

> **Digitizing Civic Services | Bridging Citizens & Government**

A full-stack **E-Governance web application** that allows citizens to file, track, and follow up on civic complaints in real-time. Departmental staff resolve them, and admins oversee the entire system — all from a single, modern platform.

---

## 📸 Application Preview

| Landing Page | Citizen Dashboard | Admin Dashboard |
|:---:|:---:|:---:|
| **"Your Complaints. Heard. Tracked. Resolved."** | Personal complaint stats & quick actions | System-wide KPIs, charts & management |

| Staff Dashboard | Login Page | Register Page |
|:---:|:---:|:---:|
| Department-filtered complaints | Role-based sign-in with demo credentials | Role selector + department + password strength |

---

## 🎯 Problem Statement

Citizens across India face difficulties when reporting civic issues like **water supply failures, electricity cuts, pothole roads, and sanitation problems**. The existing paper-based or phone-based complaint systems lack:

- ❌ Real-time tracking
- ❌ Accountability & audit trails
- ❌ Departmental routing
- ❌ Feedback mechanisms

**SmartGov** solves all of this with a transparent, trackable, role-based digital platform.

---

## ✨ Key Features

### 👤 For Citizens
- Register & login securely
- Submit complaints with category, department, location & priority
- Real-time complaint status tracking (Submitted → Resolved)
- Status timeline showing every action taken
- Rate resolved complaints with 1–5 star feedback
- Instant in-app notifications on status changes
- Delete own complaints (if still pending)

### ⚙️ For Staff (Per Department)
- Auto-filtered view — only see complaints from their department
- Acknowledge, update, and resolve complaints
- Add resolution notes to every update
- Full audit trail of actions taken
- Department-specific performance visibility

### 🏛️ For Admins
- System-wide dashboard with 8 KPI cards
- Complaints by Category bar chart
- Department Performance tracker
- Monthly complaint trend chart
- Assign complaints to specific staff members
- Update status of any complaint
- Delete any complaint
- View all registered citizens and staff

---

## 🔄 Complaint Lifecycle

```
[Citizen Files]
      ↓
  SUBMITTED  ──→  ACKNOWLEDGED  ──→  IN PROGRESS  ──→  RESOLVED  ──→  CLOSED
      ↓                ↓                                                   ↑
  REJECTED         REJECTED                                      [Citizen Confirms]
```

| Status | Description |
|--------|-------------|
| � Submitted | Complaint registered, awaiting review |
| 👁️ Acknowledged | Staff has seen and accepted it |
| 🔧 In Progress | Active work is underway |
| ✅ Resolved | Issue has been fixed |
| � Closed | Citizen confirmed resolution |
| ❌ Rejected | Complaint deemed invalid |

---

## 👥 User Roles & Access Control

| Feature | � Citizen | ⚙️ Staff | 🏛️ Admin |
|---------|:---------:|:-------:|:-------:|
| Submit Complaint | ✅ | ❌ | ❌ |
| View Own Complaints | ✅ | ❌ | ✅ All |
| View Dept. Complaints | ❌ | ✅ | ✅ All |
| Update Status | ❌ | ✅ | ✅ |
| Assign to Staff | ❌ | ❌ | ✅ |
| Delete Complaint | ✅ Own (Pending only) | ✅ Dept. | ✅ Any |
| View Analytics | ❌ | ❌ | ✅ |
| Rate Resolution | ✅ | ❌ | ❌ |
| Manage Users | ❌ | ❌ | ✅ |
| Notifications | ✅ | ✅ | ✅ |

---

## 🏗️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3 (Custom Design System), Vanilla JavaScript |
| **Backend** | Python 3.x + FastAPI (REST API) |
| **Database** | SQLite (`complaints.db`) |
| **Authentication** | JWT (JSON Web Tokens) |
| **Password Security** | SHA-256 Hashing (hashlib) |
| **Server** | Uvicorn (ASGI) |
| **API Documentation** | Swagger UI (auto-generated) |

---

## 📂 Project Structure

```
Smart Public Complaint/
│
├── backend/
│   ├── main.py                 # FastAPI app — all 15+ API routes
│   ├── database.py             # SQLite schema + seed data
│   ├── auth.py                 # JWT token + password hashing utils
│   ├── complaints.db           # SQLite database (auto-created)
│   ├── requirements.txt        # Python dependencies
│   └── uploads/                # Attached files from complaints
│
└── frontend/
    ├── index.html              # Public landing page
    ├── login.html              # Role-based login (Citizen/Staff/Admin)
    ├── register.html           # New user registration
    │
    ├── css/
    │   └── styles.css          # Full design system (dark theme, tokens)
    │
    ├── js/
    │   └── app.js              # API client + Auth + Toast + Utilities
    │
    ├── citizen/
    │   ├── dashboard.html      # Citizen home — stats + recent complaints
    │   ├── submit.html         # File a new complaint
    │   ├── my-complaints.html  # Full complaints list with filters
    │   └── profile.html        # User profile page
    │
    ├── staff/
    │   └── dashboard.html      # Staff complaint management portal
    │
    └── admin/
        ├── dashboard.html      # Admin analytics & KPIs
        ├── complaints.html     # All complaints with full management
        ├── analytics.html      # Detailed charts & trends
        └── users.html          # User & staff management
```

---

## 🗄️ Database Schema

### Tables

**`users`** — Stores all registered users
```sql
id, full_name, email, phone, password_hash, role, department, is_active, created_at
```

**`complaints`** — Every civic complaint filed
```sql
id, complaint_number, citizen_id, title, description, category, department,
location, priority, status, assigned_to, resolution_notes, attachment_path,
created_at, resolved_at
```

**`complaint_timeline`** — Full audit trail of every status change
```sql
id, complaint_id, updated_by, action, old_status, new_status, notes, created_at
```

**`notifications`** — In-app alerts for users
```sql
id, user_id, complaint_id, message, is_read, created_at
```

**`feedback`** — Citizen satisfaction ratings (1–5 stars)
```sql
id, complaint_id, citizen_id, rating, comment, created_at
```

---

## � REST API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | Public | Register new user |
| `POST` | `/api/auth/login` | Public | Login & receive JWT |
| `GET` | `/api/auth/me` | All | Current user details |
| `GET` | `/api/complaints` | All | List complaints (role-filtered) |
| `POST` | `/api/complaints` | Citizen | Submit new complaint |
| `GET` | `/api/complaints/{id}` | All | Complaint detail + timeline |
| `PUT` | `/api/complaints/{id}/status` | Staff/Admin | Update complaint status |
| `DELETE` | `/api/complaints/{id}` | Role-based | Delete complaint |
| `POST` | `/api/complaints/{id}/feedback` | Citizen | Rate resolution |
| `POST` | `/api/complaints/{id}/upload` | All | Upload file attachment |
| `GET` | `/api/notifications` | All | Get notifications |
| `PUT` | `/api/notifications/{id}/read` | All | Mark notification as read |
| `GET` | `/api/analytics/dashboard` | Admin | System analytics |
| `GET` | `/api/admin/users` | Admin | All users |
| `GET` | `/api/admin/staff` | Admin | Staff members list |

> 📖 Full interactive API docs: **http://localhost:8000/api/docs**

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- A modern web browser (Chrome, Edge, Firefox)

### Steps

```bash
# 1. Clone / Extract the project
cd "Smart Public Complaint"

# 2. Install Python dependencies
cd backend
pip install -r requirements.txt

# 3. Start the backend server
python main.py

# 4. Open the app in your browser
# → http://localhost:8000
```

The database (`complaints.db`) is **auto-created and seeded** on first run with all demo accounts.

---

## 🔑 Demo Login Credentials

| Role | Email | Password | Department |
|------|-------|----------|-----------|
| 👤 Citizen | `citizen@demo.in` | `Citizen@123` | — |
| ⚡ Staff | `electric@smartgov.in` | `Staff@123` | Electricity |
| 💧 Staff | `water@smartgov.in` | `Staff@123` | Water Supply |
| 🗑️ Staff | `sanitation@smartgov.in` | `Staff@123` | Sanitation |
| 🏗️ Staff | `infra@smartgov.in` | `Staff@123` | Infrastructure |
| 🏛️ Admin | `admin@smartgov.in` | `Admin@123` | System Admin |

---

## 🔐 Security Implementation

- **JWT Tokens** — Stateless authentication; no server-side sessions
- **Role-Based Access** — Every API endpoint validates user role before processing
- **Password Hashing** — Passwords never stored in plain text (SHA-256)
- **Input Validation** — Pydantic models enforce strict data types on all requests
- **Authorization Headers** — All protected routes require `Bearer <token>`
- **Cascade Deletes** — Deleting a complaint removes all related timeline, notification & feedback records

---

## 📊 Complaint Categories & Departments

| Category | Department | Typical Issues |
|----------|-----------|---------------|
| 💧 Water | Water Supply | No water, pipe leakage, dirty water |
| ⚡ Electricity | Electricity | Power cuts, wire damage, no street light |
| 🗑️ Sanitation | Sanitation | Garbage not collected, clogged drains |
| 🏗️ Infrastructure | Infrastructure | Potholes, broken footpaths, damaged bridges |
| 📋 Other | Administration | General civic issues |

---

## 🔮 Future Enhancements

1. 📱 **Mobile App** — React Native / Flutter citizen app
2. 📧 **Email & SMS Alerts** — Twilio / SendGrid notifications
3. 🗺️ **GPS-based Location** — Auto-detect complaint location
4. 🤖 **AI Categorization** — NLP-based auto-classify complaints
5. 🌐 **Multi-language** — Telugu, Hindi, Tamil support
6. ⏰ **Escalation Engine** — Auto-escalate unresolved complaints after N days
7. 📡 **Public City Dashboard** — Live complaint heatmap visible to all citizens


> *SmartGov — Making Governance Accountable, Transparent & Citizen-Centric* 🏛️
#   e - g o v e r n a n c e  
 
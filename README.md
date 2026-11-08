# Employee Payroll Management System (PayrollPro)

An enterprise-grade, full-stack Employee Payroll Management System designed to automate and manage organizational salary workflows, employee records, attendance, leave approval cycles, dynamic salary structures, monthly payroll processing with attendance-based loss-of-pay (LOP) calculations, PDF payslip generation, and statutory compliance reporting.

---

## 1. System Architecture

```
                                 [ Web Browser Client ]
                                           │
                        HTTP / JSON (REST) │ JWT Auth Bearer
                                           ▼
               ┌─────────────────────────────────────────────────────────┐
               │              FastAPI Application Server                 │
               │   • Static SPA Frontend Hosting (/app, /static)         │
               │   • Interactive Swagger Documentation (/docs)           │
               ├─────────────────────────────────────────────────────────┤
               │                   API v1 Endpoints                      │
               │  /auth       /employees    /departments  /designations  │
               │  /attendance /leaves       /salary       /payroll       │
               │  /payslips   /reports                                   │
               ├─────────────────────────────────────────────────────────┤
               │                  Domain Service Layer                   │
               │  • PayrollCalculator (Decimal precision, LOP engine)    │
               │  • PayslipPdfService (ReportLab document generator)     │
               │  • ReportService (pandas + openpyxl Excel exporter)     │
               │  • AttendanceService & LeaveService                     │
               ├─────────────────────────────────────────────────────────┤
               │                   SQLAlchemy ORM                        │
               └───────────────────────────┬─────────────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
             [ Primary: MySQL ]                       [ Fallback: SQLite ]
             High-concurrency orgs                    Zero-config local dev
```

---

## 2. Core Modules & Capabilities

- **Authentication & RBAC**:
  - Secure password hashing using native `bcrypt`.
  - Stateless JSON Web Tokens (`python-jose`).
  - Strict Role-Based Access Control (`ADMIN`, `HR_MANAGER`, `EMPLOYEE`).
- **Employee & Organizational Master**:
  - Full CRUD operations for employees, departments, and designations.
  - Automatic auto-generated employee codes (`EMP1001`, `EMP1002`, ...).
  - PII masking for bank account numbers (`********1012`) and encrypted storage of PAN numbers.
- **Attendance & Leave Management**:
  - Daily check-in / check-out logging with automatic working hours computation.
  - Leave balances by type (`CASUAL`, `SICK`, `PAID`) with real-time quota tracking.
  - Integrated approval workflows: approving leave automatically syncs attendance status to `ON_LEAVE`.
- **Salary Structure Engine**:
  - Configurable earnings (Basic, HRA, DA, Conveyance, Allowances, Bonus).
  - Configurable statutory deductions (Provident Fund, ESI, Professional Tax, TDS).
  - Supports both `FLAT_AMOUNT` and `PERCENTAGE` based component calculations.
- **Payroll Calculation & Disbursal**:
  - `Decimal(12, 2)` monetary arithmetic with `ROUND_HALF_UP` (zero floating-point precision loss).
  - **Loss of Pay (LOP) Formula**:
    $$\text{Unpaid LOP Deduction} = \left(\frac{\text{Monthly Salary Basis}}{\text{Payable Days}}\right) \times \text{Unpaid Days}$$
    $$\text{Final Net Salary} = \text{Gross Salary} - \text{Total Deductions} - \text{LOP Deduction}$$
  - Strict state-machine enforcement: `DRAFT` $\to$ `APPROVED` $\to$ `PAID`.
  - Database-level duplicate prevention for the same period (`employee_id` + `month` + `year`).
- **Payslip PDF Generation**:
  - Built with ReportLab to generate print-ready, professional PDF documents.
  - Features company header, employee details, side-by-side earnings/deductions, amount in words, and download tracking.
- **Reports & Data Export**:
  - Monthly Payroll Register (`.xlsx`).
  - Executive Landscape Summary (`.pdf`).
  - Departmental Cost Breakdown (`.xlsx`).
  - Statutory Tax & Deductions Compliance Register (`.xlsx`).
- **Responsive Web Dashboard**:
  - Built with Bootstrap 5, Bootstrap Icons, and Chart.js.
  - Interactive dashboards tailored for Admin, HR, and Employee self-service portals.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2, python-jose, native bcrypt
- **Document & Data Generation**: ReportLab (PDF), pandas, openpyxl (Excel)
- **Database**: MySQL 8.0+ (Primary) with automated SQLite3 graceful fallback
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Chart.js
- **Testing**: pytest 8.3.4, httpx

---

## 4. Local Setup & Installation

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-org/employee-payroll-management-system.git
cd "employee-payroll-management-system"

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment Variables
Create or verify `backend/.env`:
```env
PROJECT_NAME="Employee Payroll Management System"
VERSION="1.0.0"
API_V1_STR="/api/v1"

# Database Configuration (MySQL)
MYSQL_SERVER=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=payroll_db

# Graceful SQLite Fallback (Set True for zero-config local testing without MySQL)
USE_SQLITE_FALLBACK=True
SQLITE_DB_PATH=./payroll.db

# Security & JWT
JWT_SECRET_KEY="change_this_to_a_secure_random_hex_key_in_production"
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Default Organization Header
COMPANY_NAME="Acme Corporation Pvt. Ltd."
```

### Step 4: Initialize Database & Seed Master Data
Run the database seeder to create all database tables and populate standard users, departments, designations, leave quotas, and salary packages:
```bash
python backend/app/db/init_db.py
```

---

## 5. Running the Application

### Start the FastAPI Server
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running, access:
- **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **Alternative ReDoc UI**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- **Web Application Portal**: [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)

---

## 6. Pre-seeded Demo Accounts

| Role | Username / Email | Password | Primary Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@payroll.com` | `Admin@123` | Master control, payroll approval, wage disbursement, full reporting |
| **HR Manager** | `hr@payroll.com` | `Hr@123` | Employee CRUD, attendance logging, leave approvals, payroll batch generation |
| **Employee 1** | `employee@payroll.com` | `Employee@123` | Self-service profile (`EMP1001`), apply leaves, view/download payslips |
| **Employee 2** | `jane@payroll.com` | `Jane@123` | Self-service profile (`EMP1002`) |

---

## 7. Running the Automated Test Suite

The test suite contains **53 automated tests** covering health, authentication, RBAC, employee operations, attendance, leave deduction, salary calculation, LOP accuracy, PDF rendering, Excel export, and security edge cases:

```bash
python -m pytest backend/tests/ -v
```

Expected result:
```text
============================= 53 passed in 46.90s =============================
```

---

## 8. Production Deployment Guide

### Using Docker & Gunicorn/Uvicorn
Create a `Dockerfile` for containerized environments:
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Production Nginx Reverse Proxy Configuration
```nginx
server {
    listen 80;
    server_name payroll.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 9. License

This project is licensed under the MIT License.

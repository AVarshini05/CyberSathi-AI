# CyberSathi-AI - Local Installation Guide

> Complete step-by-step guide to run CyberSathi-AI on your local machine (Windows).

---

## Prerequisites

Install the following before proceeding:

| Tool       | Version  | Download                                      |
|------------|----------|-----------------------------------------------|
| Python     | 3.10+    | https://www.python.org/downloads/             |
| Node.js    | 18+      | https://nodejs.org/                           |
| PostgreSQL | 14+      | https://www.postgresql.org/download/windows/  |
| Git        | Latest   | https://git-scm.com/downloads                |

> **Important:** During Python installation, check **"Add Python to PATH"**.  
> During PostgreSQL installation, remember the password you set for the `postgres` user.

---

## Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd ncrp-antigravity
```

---

## Step 2: Create the Database

### Option A: Using psql (Command Line)

Open **Command Prompt** or **PowerShell** and run:

```bash
psql -U postgres -f setup_database.sql
```

Enter your PostgreSQL password when prompted.

### Option B: Using pgAdmin (GUI)

1. Open **pgAdmin 4**
2. Right-click **Databases** → **Create** → **Database**
3. Name: `ccrms`
4. Owner: `postgres`
5. Click **Save**

---

## Step 3: Configure Environment

Copy the example environment file:

```bash
copy .env.example .env
```

Edit `.env` if your PostgreSQL password is different from `postgres`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ccrms
```

---

## Step 4: Start the Application

### Quick Start (Recommended)

Double-click **`start_all.bat`** — this launches both backend and frontend in separate terminal windows.

### Manual Start

**Terminal 1 — Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Step 5: Access the Application

| Service      | URL                            |
|--------------|--------------------------------|
| Frontend     | http://localhost:5173           |
| Backend API  | http://localhost:8000           |
| API Docs     | http://localhost:8000/docs      |

### Default Login Credentials

| Role    | Email                  | Password        |
|---------|------------------------|-----------------|
| Admin   | admin@cybersathi.gov.in     | adminpassword   |
| Officer | officer@cybersathi.gov.in   | officerpassword |

> Citizens can register new accounts through the portal.

---

## Troubleshooting

### "Cannot connect to PostgreSQL"

- Ensure PostgreSQL service is running:
  - Open **Services** (Win+R → `services.msc`) → Find **postgresql** → Ensure it's **Running**
- Verify the `ccrms` database exists in pgAdmin
- Check your `.env` file has the correct password

### "Python/pip not found"

- Reinstall Python with **"Add to PATH"** checked
- Or manually add `C:\PythonXX\` and `C:\PythonXX\Scripts\` to your system PATH

### "Node.js/npm not found"

- Reinstall Node.js from https://nodejs.org/
- Restart your terminal after installation

### "Port already in use"

```bash
# Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Find and kill process on port 5173
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

---

## Project Structure

```
ncrp-antigravity/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/          # API route handlers
│   │   ├── core/            # Config, security, auth
│   │   ├── db/              # Database models, session, migrations
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── main.py          # Application entry point
│   ├── alembic.ini          # Migration configuration
│   └── requirements.txt     # Python dependencies
├── frontend/                # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page-level components
│   │   ├── services/        # API client functions
│   │   └── App.tsx          # Root component
│   ├── package.json         # Node.js dependencies
│   └── vite.config.ts       # Vite dev server configuration
├── .env                     # Environment variables (local)
├── .env.example             # Environment template
├── setup_database.sql       # Database creation script
├── start_all.bat            # Launch both servers
├── start_backend.bat        # Launch backend only
├── start_frontend.bat       # Launch frontend only
└── INSTALL_LOCAL.md         # This file
```

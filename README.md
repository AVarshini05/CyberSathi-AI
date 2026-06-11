# CyberSathi-AI

A production-grade cybercrime complaint portal inspired by India's NCRP, built for educational and portfolio purposes.

---

## Features

- **Citizen Portal** — Register, login (OTP simulation), file complaints, track status
- **Complaint Categories** — Financial fraud, women/child safety, other cybercrimes, anonymous reporting
- **Dynamic Forms** — NCRP-style multi-step complaint filing with conditional fields
- **Complaint Tracking** — Acknowledgement number lookup, status timeline, PDF receipts
- **QR Code Verification** — QR codes on receipts for authenticity checks
- **Admin Dashboard** — Manage officers, view analytics, audit trails
- **Officer Dashboard** — Assigned cases, investigation workflow, status updates
- **Suspect Repository** — Centralized suspect database with linking to complaints
- **Activity Logs** — Full audit trail for accountability
- **Notifications** — In-app notification system

---

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Frontend  | React, TypeScript, Vite, Tailwind |
| Backend   | FastAPI, SQLAlchemy, Alembic      |
| Database  | PostgreSQL                        |
| Auth      | JWT (JSON Web Tokens)             |

---

## Quick Start

### Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **PostgreSQL 14+** — [Download](https://www.postgresql.org/download/windows/)

### 1. Create the Database

```bash
psql -U postgres -f setup_database.sql
```

Or create a database named `ccrms` in pgAdmin.

### 2. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` if your PostgreSQL password differs from `postgres`.

### 3. Launch

**Windows — Double-click `start_all.bat`**

Or manually:

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### 4. Open

| Service  | URL                       |
|----------|---------------------------|
| Frontend | http://localhost:5173      |
| API Docs | http://localhost:8000/docs |

### Default Credentials

| Role    | Email                  | Password        |
|---------|------------------------|-----------------|
| Admin   | admin@cybersathi.gov.in     | adminpassword   |
| Officer | officer@cybersathi.gov.in   | officerpassword |

---

## Full Documentation

See [INSTALL_LOCAL.md](INSTALL_LOCAL.md) for detailed setup instructions, troubleshooting, and project structure.

---

## License

This project is for educational and portfolio purposes only. Not affiliated with any government entity.

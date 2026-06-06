# Cyber Crime Reporting Management System (CCRMS)

A complete production-ready online reporting and investigation workflow system inspired by India's National Cyber Crime Reporting Portal (NCRP), built for educational and portfolio review.

---

## 🌟 Key Features

1. **Multi-step Incident Reporting**: Structured forms separated into categories (Financial Fraud, Other Cyber Crime, Women & Children Related Crime).
2. **Dynamic Form Engine**: Subcategory-driven questionnaire rendering loaded dynamically from database schemas.
3. **Anonymous Reporting**: Allowed for sensitive Women/Children safety categories, ensuring reporting names are omitted.
4. **Complaint Acknowledgement System**: Automatically generates a unique, sequential acknowledgement number (e.g., `CCRMS-FF-2026-000001`).
5. **Interactive Receipt Generation**: Automatic generation of downloadable PDF receipts containing a security verification QR code linking to the status page.
6. **Timeline Complaint Tracking**: Search and visualize case progress (Submitted &rarr; Under Review &rarr; Assigned &rarr; Investigation &rarr; Closed).
7. **Citizen Dashboard**: Access case histories, upload supplemental evidence files, and view officer feedback.
8. **Suspect Repository Search**: Look up unknown numbers, emails, websites, or UPI IDs to assess risk levels (Safe, Medium, High).
9. **Back-Office Officer Console**: Manage received reports, search by indicators, review evidence attachments, and update case statuses.

---

## 🛠️ Technology Stack

* **Frontend**: React + TypeScript + Tailwind CSS (bundled via Vite)
* **Backend**: FastAPI (Python 3.11) + SQLAlchemy ORM + Uvicorn
* **Database**: PostgreSQL (v15)
* **Migrations**: Alembic
* **Authentication**: JWT Bearer Tokens + Passlib Password Hashing
* **Receipts & QR**: ReportLab PDF + python-qrcode
* **Containerization**: Docker & Docker Compose

---

## 📂 Project Architecture

```
ncrp-antigravity/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # API Route dependencies & V1 endpoints
│   │   ├── core/             # Configuration & Security (JWT, bcrypt)
│   │   ├── crud/             # SQL query helper methods
│   │   ├── db/               # Database engine, session, and seeds
│   │   ├── models/           # SQLAlchemy Declarative Models
│   │   ├── schemas/          # Pydantic schemas (validation layer)
│   │   ├── services/         # PDF and QR generator helper service
│   │   └── main.py           # App initialization & lifespan seeder
│   ├── tests/                # pytest suite
│   ├── alembic.ini           # Alembic settings
│   ├── Dockerfile            # Container build instructions
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React Application
│   ├── public/               # Public assets
│   ├── src/
│   │   ├── components/       # Layout wrappers & dynamic form engines
│   │   ├── context/          # React AuthContext (JWT + OTP simulation)
│   │   ├── pages/            # Landing page, dashboard, login views
│   │   ├── routes/           # AppRoutes and Protected routes
│   │   └── services/         # Axios API interceptor configurations
│   ├── Dockerfile            # Multi-stage containerizer
│   ├── nginx.conf            # Production Nginx Router config
│   ├── tailwind.config.js    # Customized theme theme styling
│   └── vite.config.ts        # Bundler configuration
├── docker-compose.yml        # Development Docker Compose file
├── .gitignore                # Git ignore files
└── INSTALL.md                # Quickstart guide
```

---

## 🗄️ Database Schema Design

The application utilizes a PostgreSQL schema with fully defined relations:

* `users`: Stores citizen accounts and officer logins.
* `complaints`: Primary transaction table recording categories, victim info, and status indicators.
* `complaint_categories`: Top-level groupings (Financial Fraud, Other Cyber Crime, Women and Children).
* `complaint_subcategories`: Second-level groupings (UPI Fraud, Hacking, Blackmail).
* `complaint_questions`: Form schemas containing field names, labels, options, and validations.
* `complaint_answers`: User responses mapped to specific questions and complaint records.
* `evidence_files`: Metadata log of uploaded screenshots, PDFs, or videos.
* `complaint_status`: Status transition timeline history.
* `suspect_reports`: Registry of suspect phone numbers, UPI IDs, urls, and email handles.
* `notifications`: Simulated SMS / Email transaction log.
* `audit_logs`: Activity logging for officer and system operations.

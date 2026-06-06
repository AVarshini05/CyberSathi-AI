# Setup & Installation Guide

Follow these steps to launch and test the Cyber Crime Reporting Management System (CCRMS).

---

## 🐳 Option 1: Docker Compose (Recommended)

Ensure Docker and Docker Compose are installed on your machine.

1. **Clone & Navigate**:
   ```bash
   cd ncrp-antigravity
   ```

2. **Initialize Environment Variables**:
   Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

3. **Build and Run Containers**:
   Spin up PostgreSQL, Uvicorn Backend, and Nginx Frontend:
   ```bash
   docker compose up --build -d
   ```

4. **Verify Application Links**:
   * **Frontend Portal**: `http://localhost` (served via Nginx)
   * **Backend REST API**: `http://localhost:8000`
   * **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`

5. **Stop Services**:
   ```bash
   docker compose down -v
   ```

---

## 💻 Option 2: Manual Local Setup (Without Docker)

You will need PostgreSQL (v14 or v15), Python 3.11+, and Node.js 18+ installed on your host system.

### 1. Database Setup
Create a PostgreSQL database named `ccrms` on your local server.

### 2. Backend Setup
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
5. Modify `DATABASE_URL` in your `.env` to point to your local PostgreSQL instance (e.g. `postgresql://postgres:password@localhost:5432/ccrms`).
6. Start the Uvicorn server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install npm modules:
   ```bash
   npm install
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
4. Start the Vite development server:
   ```bash
   npm run dev
   ```
5. Open your browser and navigate to `http://localhost:5173`.

---

## 🔑 Seeding & Default Credentials

Upon startup, the database is automatically synchronized and seeded with categories, subcategories, dynamic forms questions, and default test accounts:

* **Administrator Account**:
  * **Email**: `admin@ccrms.gov.in`
  * **Password**: `adminpassword`
* **Investigation Officer Account**:
  * **Email**: `officer@ccrms.gov.in`
  * **Password**: `officerpassword`

---

## 🧪 Testing User Journey

1. **Access Home Page**: Open `http://localhost` or `http://localhost:5173`.
2. **Citizen Registration**:
   * Click **Register** in the header.
   * Input name, 10-digit mobile number, and password. Submit to create the account.
3. **Citizen Login**:
   * Click **Sign In**.
   * Toggle to **Password Login** and enter mobile + password, OR toggle to **Mobile OTP Login** and enter phone number. Request OTP and enter the simulated code `123456` displayed in the blue developer notification alert.
4. **File Complaint**:
   * Click **Report Cyber Crime** or **File New Incident**.
   * Select **Financial Fraud** &rarr; **UPI Fraud** or **Internet Banking**.
   * Fill out the dynamic fields (UPI ID, Transaction ID, Bank Name, Amount).
   * Input suspect mobile/UPI details under Step 4.
   * Upload screenshot/evidence files in Step 5.
   * Review declarations and click **Confirm & Submit**.
5. **Acknowledgement & PDF**:
   * The page will redirect to the Success Acknowledgement page.
   * View the generated ACK number (e.g., `CCRMS-FF-2026-000001`).
   * Click **Download Acknowledgement PDF** to fetch the formatted PDF containing tables, details, and the verification QR code.
6. **Track Status**:
   * Click **Track Complaint** in the header.
   * Enter the ACK Number to view the visual stepping timeline progress (status shows "Submitted").
7. **Officer back-office inspection**:
   * Logout from citizen account, and click **Sign In**.
   * Standard OAuth2 credentials or Password login. Use email: `officer@ccrms.gov.in` and password: `officerpassword`.
   * Since this is an officer, clicking **Dashboard** opens the **Officer Console**.
   * View the newly filed complaint, click **Inspect** to review citizen answers, suspect profiles, and attached screenshots.
   * Use the **Action Panel** on the right to update the status to "Under Review" or "Investigation In Progress", adding remarks.
   * Verify on the **Track Complaint** page that the timeline step has updated reactively!
8. **Suspect Search**:
   * Go to **Suspect Search** page.
   * Enter the suspect phone number or UPI ID reported in Step 4.
   * Verify the repository warns you with "Medium/High Risk" levels and counts the linked complaints!

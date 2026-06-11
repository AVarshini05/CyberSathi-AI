@echo off
title CCRMS Backend Server
echo ================================================
echo   CCRMS Backend Server
echo ================================================
echo.

cd /d "%~dp0backend"

echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet

echo [3/3] Starting FastAPI server on http://localhost:8000 ...
echo.
echo   API Docs:     http://localhost:8000/docs
echo   Admin Login:  admin@ccrms.gov.in / adminpassword
echo   Officer Login: officer@ccrms.gov.in / officerpassword
echo.
echo Press Ctrl+C to stop the server.
echo ================================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

@echo off
title CCRMS Frontend Server
echo ================================================
echo   CCRMS Frontend Server
echo ================================================
echo.

cd /d "%~dp0frontend"

echo [1/3] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
call npm install --silent

echo [3/3] Starting Vite dev server on http://localhost:5173 ...
echo.
echo   Frontend:     http://localhost:5173
echo   (Backend must be running on port 8000)
echo.
echo Press Ctrl+C to stop the server.
echo ================================================
echo.

call npm run dev

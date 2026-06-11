@echo off
title CCRMS - Starting All Services
echo ================================================
echo   CCRMS - Cyber Crime Reporting System
echo   Starting All Services
echo ================================================
echo.

echo [1/4] Checking PostgreSQL...
pg_isready -h localhost -p 5432 >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: PostgreSQL does not appear to be running on localhost:5432.
    echo Please start PostgreSQL before continuing.
    echo.
    echo If PostgreSQL is installed but pg_isready is not in PATH,
    echo you can ignore this warning if you know PostgreSQL is running.
    echo.
    pause
)

echo [2/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [3/4] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH.
    pause
    exit /b 1
)

echo [4/4] Launching servers...
echo.

:: Start backend in a new terminal window
start "CCRMS Backend" cmd /k "%~dp0start_backend.bat"

:: Wait 3 seconds for backend to boot
timeout /t 3 /nobreak >nul

:: Start frontend in a new terminal window
start "CCRMS Frontend" cmd /k "%~dp0start_frontend.bat"

echo.
echo ================================================
echo   Both servers launched in separate windows!
echo.
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo   Close this window anytime.
echo ================================================
pause

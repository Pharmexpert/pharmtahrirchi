@echo off
setlocal
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ==================================================
echo   Pharma Expert AI Platform - LOCAL START
echo ==================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+
    pause & exit /b 1
)
echo [OK] Python ready.

echo [1/3] Starting Backend (port 8000)...
start "Pharma Backend" /D "%ROOT_DIR%backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

if not exist "%ROOT_DIR%frontend\node_modules" (
    echo [!] Installing frontend packages...
    cd /d "%ROOT_DIR%frontend" & npm install --legacy-peer-deps & cd /d "%ROOT_DIR%"
)

echo [2/3] Starting Frontend (port 3001)...
start "Pharma Frontend" /D "%ROOT_DIR%frontend" cmd /k "npm run dev -- -p 3001"

echo [3/3] Opening browser in 8 seconds...
timeout /t 8 /nobreak >nul
start http://localhost:3001

echo.
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8000/docs
echo ==================================================
pause

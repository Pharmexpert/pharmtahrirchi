@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ====================================================
echo   PHARMA EXPERT AI  ^|  LOCAL DEVELOPMENT START
echo ====================================================
echo   Backend:   http://localhost:8000/docs
echo   Frontend:  http://localhost:3001
echo ====================================================
echo.

:: ── Check Python ───────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+
    pause & exit /b 1
)
echo [OK] Python found.

:: ── Check Node ─────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Node.js not found. Frontend cannot start.
) else (
    echo [OK] Node.js found.
)

:: ── Set backend env (local dev) ────────────────────
if exist "%ROOT%backend\.env" (
    echo [OK] Backend .env loaded.
) else (
    echo [WARN] backend\.env not found. Creating default...
    echo GOOGLE_API_KEY=AIzaSyCfB5C5786gTxdt0nmgNHSvJBKLRPtDZ-g> "%ROOT%backend\.env"
    echo ANTHROPIC_API_KEY=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>> "%ROOT%backend\.env"
)

:: ── Set frontend env (local dev pointing to local backend) ──
echo NEXT_PUBLIC_API_URL=http://localhost:8000> "%ROOT%frontend\.env.local"
echo [OK] Frontend .env.local set to local backend.

:: ── Install frontend deps if needed ────────────────
if not exist "%ROOT%frontend\node_modules" (
    echo [!] Installing frontend packages (first time)...
    cd /d "%ROOT%frontend"
    call npm install --legacy-peer-deps
    cd /d "%ROOT%"
)

:: ── Start Backend ──────────────────────────────────
echo.
echo [1/2] Starting Backend on port 8000...
start "Pharma Backend" /D "%ROOT%backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload & pause"

:: Wait for backend to initialize
timeout /t 4 /nobreak >nul

:: ── Start Frontend ─────────────────────────────────
echo [2/2] Starting Frontend on port 3001...
start "Pharma Frontend" /D "%ROOT%frontend" cmd /k "npm run dev -- -p 3001 & pause"

:: ── Open browser ───────────────────────────────────
echo.
echo Waiting for services to start...
timeout /t 8 /nobreak >nul
start http://localhost:3001

echo.
echo ====================================================
echo   [RUNNING]
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8000/docs
echo   API Docs:  http://localhost:8000/openapi.json
echo.
echo   Production sites:
echo   Frontend:  https://frontend-dun-nine-30.vercel.app
echo   Backend:   https://pharma-backend-production-38bb.up.railway.app/docs
echo ====================================================
echo.
echo   To DEPLOY changes to production:
echo   Run: deploy.bat
echo ====================================================
pause

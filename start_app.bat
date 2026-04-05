@echo off
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ================================================
echo   PHARMA EXPERT AI - LOCAL DEVELOPMENT START
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8000/docs
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found.

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Node.js not found. Frontend will not start.
) else (
    echo [OK] Node.js found.
)

:: Create backend .env if missing
if not exist "%ROOT%backend\.env" (
    echo [INFO] Creating backend .env...
    echo GOOGLE_API_KEY=AIzaSyCfB5C5786gTxdt0nmgNHSvJBKLRPtDZ-g> "%ROOT%backend\.env"
    echo ANTHROPIC_API_KEY=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>> "%ROOT%backend\.env"
)

:: Set frontend to use LOCAL backend for dev
echo NEXT_PUBLIC_API_URL=http://localhost:8000> "%ROOT%frontend\.env.local"
echo [OK] Frontend will connect to local backend.

:: Install frontend packages if not present
if not exist "%ROOT%frontend\node_modules" (
    echo [!] Installing frontend packages (first time, please wait)...
    cd /d "%ROOT%frontend"
    call npm install --legacy-peer-deps
    cd /d "%ROOT%"
)

:: Start Backend
echo.
echo [1/2] Starting Backend on port 8000...
start "Pharma Backend" /D "%ROOT%backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for backend to load
timeout /t 4 /nobreak >nul

:: Start Frontend
echo [2/2] Starting Frontend on port 3001...
start "Pharma Frontend" /D "%ROOT%frontend" cmd /k "npm run dev -- -p 3001"

:: Open browser
echo.
echo Waiting 8 seconds for services...
timeout /t 8 /nobreak >nul
start http://localhost:3001

echo.
echo ================================================
echo   LOCAL:
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8000/docs
echo.
echo   PRODUCTION:
echo   Frontend:  https://frontend-dun-nine-30.vercel.app
echo   Backend:   https://pharma-backend-production-38bb.up.railway.app/docs
echo.
echo   To deploy to production: run deploy.bat
echo ================================================
echo.
pause
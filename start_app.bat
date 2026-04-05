@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ================================================
echo   PHARMA EXPERT AI - LOCAL STARTUP
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo ================================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

:: ------------------------------------------------
:: Check prerequisites
:: ------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+
    pause
    exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+
    pause
    exit /b 1
)

:: ------------------------------------------------
:: Kill any existing processes on ports 8000/3000
:: ------------------------------------------------
echo [1/4] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo    [OK] Ports 8000, 3000 cleared.

:: ------------------------------------------------
:: Create required directories
:: ------------------------------------------------
echo [2/4] Preparing directories...
if not exist "%BACKEND%\uploads" mkdir "%BACKEND%\uploads"
if not exist "%BACKEND%\temp_files" mkdir "%BACKEND%\temp_files"
if not exist "%BACKEND%\temp_files\imgs" mkdir "%BACKEND%\temp_files\imgs"
echo    [OK] Directories ready.

:: ------------------------------------------------
:: Start Backend (in new window)
:: ------------------------------------------------
echo [3/4] Starting backend on http://localhost:8000 ...
start "Pharma Backend" cmd /k "cd /d "%BACKEND%" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo    [OK] Backend starting (new window).

:: ------------------------------------------------
:: Start Frontend (in new window)
:: ------------------------------------------------
echo [4/4] Starting frontend on http://localhost:3000 ...
start "Pharma Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"
echo    [OK] Frontend starting (new window).

:: ------------------------------------------------
:: Wait and verify
:: ------------------------------------------------
echo.
echo Waiting 10 seconds for servers to start...
timeout /t 10 /nobreak >nul

echo.
echo Verifying...
python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/api/specialists',timeout=5); print('  [OK] Backend: HTTP',r.status)" 2>nul
if errorlevel 1 echo   [WAIT] Backend still loading (BERT model takes ~30s)...

python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:3000',timeout=5); print('  [OK] Frontend: HTTP',r.status)" 2>nul
if errorlevel 1 echo   [WAIT] Frontend still compiling...

echo.
echo ================================================
echo   SERVERS RUNNING:
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo   Close the terminal windows to stop.
echo ================================================
echo.
pause

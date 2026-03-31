@echo off
setlocal

:: Get the directory of the batch file
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo --------------------------------------------------
echo   Pharmaceutical Document Aligner - STARTING
echo --------------------------------------------------

:: Verify Virtual Environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
    echo Please make sure you have installed the backend dependencies.
    pause
    exit /b 1
)

:: Backend - FastAPI
echo [1/3] Starting Backend (FastAPI)...
:: Using /k instead of /c for backend to keep window open on error
start "Pharma Backend" /D "%ROOT_DIR%backend" cmd /k "..\.venv\Scripts\python.exe main.py"

:: Verify node_modules for frontend
if not exist "frontend\node_modules" (
    echo [ERROR] frontend\node_modules not found.
    echo Please run 'npm install' in the frontend directory.
    pause
    exit /b 1
)

:: Frontend - Next.js
echo [2/3] Starting Frontend (Next.js)...
start "Pharma Frontend" /D "%ROOT_DIR%frontend" cmd /c "npm run dev -- -p 3001"

:: Browser
echo [3/3] Opening browser in 5 seconds...
timeout /t 5 /nobreak > nul
start http://localhost:3001

echo.
echo --------------------------------------------------
echo   App running at: http://localhost:3001
echo   Backend port: 8000
echo --------------------------------------------------
echo.
pause

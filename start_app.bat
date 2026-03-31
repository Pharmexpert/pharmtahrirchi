@echo off
setlocal

echo --------------------------------------------------
echo   Pharmaceutical Document Aligner - STARTING
echo --------------------------------------------------

:: Backend - FastAPI
echo [1/3] Starting Backend (FastAPI)...
start "Pharma Backend" /D backend cmd /c "python main.py"

:: Frontend - Next.js
echo [2/3] Starting Frontend (Next.js)...
start "Pharma Frontend" /D frontend cmd /c "npm run dev -- -p 3001"

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

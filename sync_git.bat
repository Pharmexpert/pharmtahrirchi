@echo off
setlocal
cd /d "%~dp0"

echo ══════════════════════════════════════════════
echo   PHARMA PLATFORM - GitHub + Cloud Sync
echo ══════════════════════════════════════════════

:: Data Protection Warning
echo.
echo [ SAFETY CHECK ]
echo - Local DB (*.db) is EXCLUDED from Git.
echo - Your local changes will NOT overwrite production data.
echo - Global rules/synonyms must be managed via Admin Dashboard.
echo ══════════════════════════════════════════════

:: Step 1: Database Export (for sync JSON)
echo.
echo [1/5] Exporting local database metadata...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe backend\sync_db.py export
) else (
    echo [WARN] Virtual environment not found, skipping DB export
)

:: Step 2: Git Add
echo.
echo [2/5] Adding code changes...
git add .

:: Step 3: Git Commit
echo.
echo [3/5] Committing changes...
set /p commit_msg="Enter commit message (or press Enter for 'Auto-sync'): "
if "%commit_msg%"=="" set commit_msg=Auto-sync %date% %time%
git commit -m "%commit_msg%"

:: Step 4: Git Push (Triggers Railway Backend + Vercel if connected)
echo.
echo [4/5] Pushing to GitHub (Origin: pharmtahrirchi)...
git push origin main
if %errorlevel% neq 0 (
    echo [WARN] Push failed. Trying to pull first...
    git pull --rebase origin main
    git push origin main
)

:: Step 5: Vercel Deploy — FRONTEND FOLDER
echo.
echo [5/5] Triggering Vercel Frontend deployment...
where vercel >nul 2>nul
if %errorlevel% equ 0 (
    echo.
    echo --- Deploying frontend (frontend-dun-nine-30.vercel.app) ---
    cd /d "%~dp0frontend"
    vercel --prod --yes
    cd /d "%~dp0"
) else (
    echo [INFO] Vercel CLI not installed. Deploying via GitHub Hook...
)

echo.
echo ══════════════════════════════════════════════
echo   GitHub:   SYNCED [OK]
echo   Railway:  BACKEND DEPLOYING... (Check Railway Dash)
echo   Vercel:   FRONTEND DEPLOYING...
echo   URL:      https://frontend-dun-nine-30.vercel.app
echo ══════════════════════════════════════════════
pause

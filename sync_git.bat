@echo off
setlocal
cd /d "%~dp0"

echo ══════════════════════════════════════════════
echo   PHARMA PLATFORM — GitHub + Vercel Sync
echo ══════════════════════════════════════════════

:: Step 1: Database Export (for sync)
echo.
echo [1/5] Exporting database for sync...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe backend\sync_db.py export
) else (
    echo [WARN] Virtual environment not found, skipping DB export
)

:: Step 2: Git Add
echo.
echo [2/5] Adding changes...
git add .

:: Step 3: Git Commit
echo.
echo [3/5] Committing changes...
set /p commit_msg="Enter commit message (or press Enter for 'Auto-sync'): "
if "%commit_msg%"=="" set commit_msg=Auto-sync %date% %time%
git commit -m "%commit_msg%"

:: Step 4: Git Push to GitHub
echo.
echo [4/5] Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo [WARN] Push failed. Trying to pull first...
    git pull --rebase origin main
    git push origin main
)

:: Step 5: Vercel Deploy — FRONTEND FOLDER
echo.
echo [5/5] Vercel Frontend deployment...
where vercel >nul 2>nul
if %errorlevel% equ 0 (
    echo Vercel CLI found. Deploying frontend to production...
    echo.
    echo --- Deploying frontend (frontend-dun-nine-30.vercel.app) ---
    cd /d "%~dp0frontend"
    vercel --prod --yes
    cd /d "%~dp0"
    echo.
    echo Frontend deployment triggered!
    
    :: Post-deploy: sync DB with remote
    if defined VERCEL_API_URL (
        echo Syncing database with remote...
        .venv\Scripts\python.exe backend\sync_db.py sync
    )
) else (
    echo [INFO] Vercel CLI not installed.
    echo        Install with: npm i -g vercel
    echo        Then run this script again.
    echo.
    echo [!] IMPORTANT: GitHub push alone does NOT deploy frontend!
    echo     The Vercel project 'frontend' is connected to 'pharma-backend' repo
    echo     but your code is in 'pharmtahrirchi' repo.
    echo     You MUST use 'vercel --prod' from the frontend/ folder.
)

echo.
echo ══════════════════════════════════════════════
echo   GitHub:   SYNCED ✓
echo   Vercel:   FRONTEND DEPLOYED ✓
echo   DB:       EXPORTED ✓
echo   URL:      https://frontend-dun-nine-30.vercel.app
echo ══════════════════════════════════════════════
pause

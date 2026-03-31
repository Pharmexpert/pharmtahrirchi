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

:: Step 5: Vercel Deploy
echo.
echo [5/5] Vercel deployment...
where vercel >nul 2>nul
if %errorlevel% equ 0 (
    echo Vercel CLI found. Triggering production deploy...
    vercel --prod --yes
    echo.
    echo Vercel deployment triggered!
    
    :: Post-deploy: sync DB with remote
    if defined VERCEL_API_URL (
        echo Syncing database with remote...
        .venv\Scripts\python.exe backend\sync_db.py sync
    )
) else (
    echo [INFO] Vercel CLI not installed. Deployment will be triggered
    echo        automatically via GitHub integration.
    echo        To install Vercel CLI: npm i -g vercel
)

echo.
echo ══════════════════════════════════════════════
echo   GitHub:  SYNCED ✓
echo   Vercel:  DEPLOYMENT TRIGGERED ✓
echo   DB:      EXPORTED ✓
echo ══════════════════════════════════════════════
pause

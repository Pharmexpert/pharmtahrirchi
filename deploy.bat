@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ================================================
echo   PHARMA EXPERT AI - PRODUCTION DEPLOY
echo   Frontend: https://frontend-dun-nine-30.vercel.app
echo   Backend:  https://pharma-backend-production-38bb.up.railway.app
echo ================================================
echo.

set "ROOT=%~dp0"
set "BACKEND_SRC=%ROOT%backend"
set "BACKEND_DST=%ROOT%pharma-backend-deploy"
set "FRONTEND_DIR=%ROOT%frontend"

:: ------------------------------------------------
:: STEP 1: Sync backend files to Railway repo
:: ------------------------------------------------
echo [1/5] Syncing backend files to Railway repo...
for %%f in ("%BACKEND_SRC%\*.py") do (
    xcopy /Y /Q "%%f" "%BACKEND_DST%\" >nul 2>&1
)
if exist "%BACKEND_SRC%\requirements.txt" xcopy /Y /Q "%BACKEND_SRC%\requirements.txt" "%BACKEND_DST%\" >nul 2>&1
if exist "%BACKEND_SRC%\Procfile" xcopy /Y /Q "%BACKEND_SRC%\Procfile" "%BACKEND_DST%\" >nul 2>&1
if exist "%BACKEND_SRC%\startup.py" xcopy /Y /Q "%BACKEND_SRC%\startup.py" "%BACKEND_DST%\" >nul 2>&1
echo    [OK] Backend files synced.

:: ------------------------------------------------
:: STEP 2: Push backend to Railway
:: ------------------------------------------------
echo.
echo [2/5] Pushing backend to Railway...
cd /d "%BACKEND_DST%"
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Deploy: Backend sync %DATE% %TIME:~0,5%"
    git push origin main
    if errorlevel 1 (
        git pull --rebase origin main
        git push origin main
    )
    echo    [OK] Railway backend deploy triggered.
) else (
    echo    [INFO] No backend changes. Railway skipped.
)

:: ------------------------------------------------
:: STEP 3: Commit monorepo changes
:: ------------------------------------------------
echo.
echo [3/5] Committing frontend changes...
cd /d "%ROOT%"
git add -A -- ":(exclude)pharma-backend-deploy" ":(exclude)*.db" ":(exclude).venv" ":(exclude)temp_files"

git diff --cached --quiet
if errorlevel 1 (
    set COMMIT_MSG=
    set /p COMMIT_MSG="  Commit message (Enter=Auto): "
    if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Deploy: Auto-sync %DATE% %TIME:~0,5%"
    git commit -m "!COMMIT_MSG!"
    git push origin main
    if errorlevel 1 (
        git pull --rebase origin main
        git push origin main
    )
    echo    [OK] Monorepo pushed.
) else (
    echo    [INFO] No monorepo changes.
)

:: ------------------------------------------------
:: STEP 4: Deploy frontend to Vercel
:: ------------------------------------------------
echo.
echo [4/5] Deploying frontend to Vercel (production)...
cd /d "%FRONTEND_DIR%"
where npx >nul 2>&1
if errorlevel 1 (
    echo    [ERROR] Node.js not found. Install Node.js 18+
    goto vercel_skip
)
npx vercel --prod --yes
if errorlevel 1 (
    echo    [WARN] Vercel deploy issue. Check vercel.com
) else (
    echo    [OK] Frontend deployed to Vercel.
)
:vercel_skip

:: ------------------------------------------------
:: STEP 5: Verify endpoints
:: ------------------------------------------------
echo.
echo [5/5] Verifying production...
cd /d "%ROOT%"
echo    Checking backend...
python -c "import urllib.request; r=urllib.request.urlopen('https://pharma-backend-production-38bb.up.railway.app/api/linguistic/all',timeout=10); print('   [OK] Backend: HTTP',r.status)"
echo    Checking frontend...
python -c "import urllib.request; r=urllib.request.urlopen('https://frontend-dun-nine-30.vercel.app',timeout=10); print('   [OK] Frontend: HTTP',r.status)"

echo.
echo ================================================
echo   DEPLOY COMPLETE!
echo   Frontend:  https://frontend-dun-nine-30.vercel.app
echo   Backend:   https://pharma-backend-production-38bb.up.railway.app/docs
echo ================================================
echo.
pause
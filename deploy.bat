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
:: STEP 1: Sync ALL backend files to Railway repo
:: ------------------------------------------------
echo [1/5] Syncing backend files to Railway repo...

:: Sync root-level .py files
for %%f in ("%BACKEND_SRC%\*.py") do (
    xcopy /Y /Q "%%f" "%BACKEND_DST%\" >nul 2>&1
)

:: Sync routes/ directory (CRITICAL - modular architecture)
if not exist "%BACKEND_DST%\routes" mkdir "%BACKEND_DST%\routes"
xcopy /Y /Q "%BACKEND_SRC%\routes\*.py" "%BACKEND_DST%\routes\" >nul 2>&1

:: Sync config files
if exist "%BACKEND_SRC%\requirements.txt" xcopy /Y /Q "%BACKEND_SRC%\requirements.txt" "%BACKEND_DST%\" >nul 2>&1
if exist "%BACKEND_SRC%\Procfile" xcopy /Y /Q "%BACKEND_SRC%\Procfile" "%BACKEND_DST%\" >nul 2>&1
if exist "%BACKEND_SRC%\.env.example" xcopy /Y /Q "%BACKEND_SRC%\.env.example" "%BACKEND_DST%\" >nul 2>&1

echo    [OK] Backend files synced (including routes/).

:: ------------------------------------------------
:: STEP 2: Push backend to Railway
:: ------------------------------------------------
echo.
echo [2/5] Pushing backend to Railway...
cd /d "%BACKEND_DST%"
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Deploy: Auto-sync %DATE% %TIME:~0,5%"
    git push origin main
    if errorlevel 1 (
        echo    [WARN] Push failed, trying rebase...
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
echo [3/5] Committing monorepo changes...
cd /d "%ROOT%"
git add -A -- ":(exclude)pharma-backend-deploy" ":(exclude)*.db" ":(exclude).venv" ":(exclude)temp_files" ":(exclude).claude"

git diff --cached --quiet
if errorlevel 1 (
    set COMMIT_MSG=
    set /p COMMIT_MSG="  Commit message (Enter=Auto): "
    if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Deploy: Auto-sync %DATE% %TIME:~0,5%"
    git commit -m "!COMMIT_MSG!"
    git push origin main
    if errorlevel 1 (
        echo    [WARN] Push failed, trying rebase...
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
echo [4/5] Deploying frontend to Vercel...
cd /d "%FRONTEND_DIR%"
where npx >nul 2>&1
if errorlevel 1 (
    echo    [SKIP] npx not found. Vercel auto-deploys from main push.
    goto vercel_done
)
npx vercel --prod --yes
if errorlevel 1 (
    echo    [WARN] Vercel CLI issue. Check https://vercel.com — auto-deploy from main may still work.
) else (
    echo    [OK] Frontend deployed to Vercel.
)
:vercel_done

:: ------------------------------------------------
:: STEP 5: Verify production (with retry)
:: ------------------------------------------------
echo.
echo [5/5] Verifying production (Railway needs ~3 min for BERT)...
cd /d "%ROOT%"

:: Quick check
python -c "import urllib.request; r=urllib.request.urlopen('https://pharma-backend-production-38bb.up.railway.app/api/specialists',timeout=10); print('   [OK] Backend: HTTP',r.status)" 2>nul
if errorlevel 1 (
    echo    [WAIT] Backend not ready yet - Railway is rebuilding with BERT model.
    echo    [WAIT] This takes 3-5 minutes. Check: https://pharma-backend-production-38bb.up.railway.app/docs
)

python -c "import urllib.request; r=urllib.request.urlopen('https://frontend-dun-nine-30.vercel.app',timeout=10); print('   [OK] Frontend: HTTP',r.status)" 2>nul
if errorlevel 1 (
    echo    [WAIT] Frontend rebuilding on Vercel...
)

echo.
echo ================================================
echo   DEPLOY TRIGGERED!
echo   Frontend:  https://frontend-dun-nine-30.vercel.app
echo   Backend:   https://pharma-backend-production-38bb.up.railway.app/docs
echo   Railway:   https://railway.com/project/e0f4d961-40b7-429a-a4f1-c7241011297a
echo ================================================
echo.
pause

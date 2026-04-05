@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
cd /d "%~dp0"

:: ════════════════════════════════════════════════════
::   PHARMA EXPERT AI — PRODUCTION DEPLOY SCRIPT
::   Frontend → Vercel (frontend-dun-nine-30.vercel.app)
::   Backend  → Railway (pharma-backend-production-38bb.up.railway.app)
:: ════════════════════════════════════════════════════

set "ROOT=%~dp0"
set "BACKEND_SRC=%ROOT%backend"
set "BACKEND_DST=%ROOT%pharma-backend-deploy"
set "FRONTEND_DIR=%ROOT%frontend"
set "FRONTEND_URL=https://frontend-dun-nine-30.vercel.app"
set "BACKEND_URL=https://pharma-backend-production-38bb.up.railway.app"

echo.
echo ====================================================
echo   PHARMA EXPERT AI  ^|  PRODUCTION DEPLOY
echo ====================================================
echo   Frontend: %FRONTEND_URL%
echo   Backend:  %BACKEND_URL%
echo ====================================================
echo.

:: ────────────────────────────────────────────────────
:: STEP 1: Sync backend files to Railway deploy repo
:: ────────────────────────────────────────────────────
echo [1/5] Syncing backend files to Railway repo...
set "SYNC_COUNT=0"
for %%f in ("%BACKEND_SRC%\*.py") do (
    xcopy /Y /Q "%%f" "%BACKEND_DST%\" >nul 2>&1
    set /a SYNC_COUNT+=1
)
if exist "%BACKEND_SRC%\requirements.txt" (
    xcopy /Y /Q "%BACKEND_SRC%\requirements.txt" "%BACKEND_DST%\" >nul 2>&1
)
if exist "%BACKEND_SRC%\startup.py" (
    xcopy /Y /Q "%BACKEND_SRC%\startup.py" "%BACKEND_DST%\" >nul 2>&1
)
if exist "%BACKEND_SRC%\processor.py" (
    xcopy /Y /Q "%BACKEND_SRC%\processor.py" "%BACKEND_DST%\" >nul 2>&1
)
if exist "%BACKEND_SRC%\Procfile" (
    xcopy /Y /Q "%BACKEND_SRC%\Procfile" "%BACKEND_DST%\" >nul 2>&1
)
echo    [OK] Backend files synced.

:: ────────────────────────────────────────────────────
:: STEP 2: Push backend to Railway (pharma-backend repo)
:: ────────────────────────────────────────────────────
echo.
echo [2/5] Pushing backend to Railway...
cd /d "%BACKEND_DST%"
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Deploy: Backend sync %DATE% %TIME:~0,5%"
    git push origin main
    if errorlevel 1 (
        echo    [WARN] Railway push failed. Retrying with pull...
        git pull --rebase origin main
        git push origin main
    )
    echo    [OK] Railway backend deploy triggered.
) else (
    echo    [INFO] No backend changes. Railway skip.
)

:: ────────────────────────────────────────────────────
:: STEP 3: Commit all monorepo changes (pharmtahrirchi)
:: ────────────────────────────────────────────────────
echo.
echo [3/5] Committing monorepo changes...
cd /d "%ROOT%"
git add -A -- ":(exclude)pharma-backend-deploy" ":(exclude)*.db" ":(exclude).venv" ":(exclude)temp_files"

git diff --cached --quiet
if errorlevel 1 (
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
    echo    [INFO] No monorepo changes to commit.
)

:: ────────────────────────────────────────────────────
:: STEP 4: Deploy frontend to Vercel (production)
:: ────────────────────────────────────────────────────
echo.
echo [4/5] Deploying frontend to Vercel...
cd /d "%FRONTEND_DIR%"
where npx >nul 2>&1
if errorlevel 1 (
    echo    [ERROR] Node.js/npx not found! Install Node.js 18+.
    goto :skip_vercel
)
call npx vercel --prod --yes 2>&1 | findstr /i "error\|fail\|ready\|aliased\|production\|building"
if errorlevel 1 (
    echo    [WARN] Vercel deploy may have issues. Check vercel.com
) else (
    echo    [OK] Vercel frontend deployed.
)
:skip_vercel

:: ────────────────────────────────────────────────────
:: STEP 5: Verify production endpoints
:: ────────────────────────────────────────────────────
echo.
echo [5/5] Verifying production endpoints...
cd /d "%ROOT%"

python -c "
import urllib.request, json, sys
checks = [
    ('Backend Health',  'https://pharma-backend-production-38bb.up.railway.app/api/linguistic/all'),
    ('Frontend',        'https://frontend-dun-nine-30.vercel.app'),
]
all_ok = True
for name, url in checks:
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'deploy-check/1.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            status = r.status
            ok = status < 400
            print(f'   [{\"OK\" if ok else \"FAIL\"}] {name}: HTTP {status}')
            if not ok: all_ok = False
    except Exception as e:
        print(f'   [ERR] {name}: {e}')
        all_ok = False
sys.exit(0 if all_ok else 1)
" 2>&1

:: ════════════════════════════════════════════════════
echo.
echo ====================================================
echo   DEPLOY COMPLETE!
echo   Frontend:  %FRONTEND_URL%
echo   Backend:   %BACKEND_URL%/docs
echo ====================================================
echo.
pause

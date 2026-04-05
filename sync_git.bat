@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ================================================
echo   PHARMA EXPERT AI - GIT SYNC
echo   Syncs monorepo + Railway backend repo
echo ================================================
echo.

set "ROOT=%~dp0"
set "BACKEND_SRC=%ROOT%backend"
set "BACKEND_DST=%ROOT%pharma-backend-deploy"

:: ------------------------------------------------
:: STEP 1: Sync backend files to Railway deploy repo
:: ------------------------------------------------
echo [1/4] Syncing backend to Railway repo...

:: Root-level .py files
for %%f in ("%BACKEND_SRC%\*.py") do (
    xcopy /Y /Q "%%f" "%BACKEND_DST%\" >nul 2>&1
)

:: Routes directory (CRITICAL for modular architecture)
if not exist "%BACKEND_DST%\routes" mkdir "%BACKEND_DST%\routes"
xcopy /Y /Q "%BACKEND_SRC%\routes\*.py" "%BACKEND_DST%\routes\" >nul 2>&1

:: Config files
xcopy /Y /Q "%BACKEND_SRC%\requirements.txt" "%BACKEND_DST%\" >nul 2>&1
xcopy /Y /Q "%BACKEND_SRC%\Procfile" "%BACKEND_DST%\" >nul 2>&1
xcopy /Y /Q "%BACKEND_SRC%\.env.example" "%BACKEND_DST%\" >nul 2>&1

echo    [OK] Backend files synced (including routes/).

:: ------------------------------------------------
:: STEP 2: Commit Railway deploy repo
:: ------------------------------------------------
echo [2/4] Committing Railway repo...
cd /d "%BACKEND_DST%"
git add -A
git diff --cached --quiet
if errorlevel 1 (
    set MSG=
    set /p MSG="  Railway commit message (Enter=Auto): "
    if "!MSG!"=="" set "MSG=Sync: Backend %DATE% %TIME:~0,5%"
    git commit -m "!MSG!"
    echo    [OK] Railway repo committed.
) else (
    echo    [INFO] No Railway changes.
)

:: ------------------------------------------------
:: STEP 3: Commit monorepo
:: ------------------------------------------------
echo [3/4] Committing monorepo...
cd /d "%ROOT%"
git add -A -- ":(exclude)pharma-backend-deploy" ":(exclude)*.db" ":(exclude).venv" ":(exclude)temp_files" ":(exclude).claude"

git diff --cached --quiet
if errorlevel 1 (
    set MSG=
    set /p MSG="  Monorepo commit message (Enter=Auto): "
    if "!MSG!"=="" set "MSG=Sync: Auto-sync %DATE% %TIME:~0,5%"
    git commit -m "!MSG!"
    echo    [OK] Monorepo committed.
) else (
    echo    [INFO] No monorepo changes.
)

:: ------------------------------------------------
:: STEP 4: Push both repos
:: ------------------------------------------------
echo [4/4] Pushing to remotes...

echo    Pushing Railway backend...
cd /d "%BACKEND_DST%"
git push origin main 2>nul
if errorlevel 1 (
    echo    [WARN] Railway push failed. Trying rebase...
    git pull --rebase origin main
    git push origin main
)

echo    Pushing monorepo...
cd /d "%ROOT%"
git push origin main 2>nul
if errorlevel 1 (
    echo    [WARN] Monorepo push failed. Trying rebase...
    git pull --rebase origin main
    git push origin main
)

echo.
echo ================================================
echo   GIT SYNC COMPLETE!
echo   Monorepo:  pushed to origin/main
echo   Railway:   pushed to pharma-backend/main
echo ================================================
echo.
pause

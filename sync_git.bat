@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Adding changes...
git add .

echo.
echo [2/3] Committing changes...
set /p commit_msg="Enter commit message (or press Enter for 'Auto-sync'): "
if "%commit_msg%"=="" set commit_msg=Auto-sync %date% %time%
git commit -m "%commit_msg%"

echo.
echo [3/3] Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo Project successfully synced to GitHub!
echo ========================================
pause

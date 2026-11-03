@echo off
setlocal
cd /d "%~dp0"

echo.
echo   Stopping job-scout...
docker compose down
echo   [OK] Stopped.
echo.
pause
exit /b 0
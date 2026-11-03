@echo off
setlocal
cd /d "%~dp0"

echo.
echo   job-scout
echo   ==========
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo   [XX] Docker not found. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo   [..] Docker Desktop is not running, starting it...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    )
    echo   [..] Waiting up to 90 seconds for Docker...
    for /l %%i in (1,1,45) do (
        timeout /t 2 /nobreak >nul 2>&1
        docker info >nul 2>nul && goto :docker_ready
    )
    echo   [XX] Docker still not ready. Start Docker Desktop manually and retry.
    pause
    exit /b 1
)
:docker_ready

echo   [..] Starting containers...
docker compose up -d
if errorlevel 1 (
    echo   [XX] Failed to start. Run this to see why:  docker compose logs
    pause
    exit /b 1
)

rem ??????????
curl -s -m 3 http://127.0.0.1:8001/health >nul 2>nul
if not errorlevel 1 goto :ready

echo   [..] Waiting for API...
for /l %%i in (1,1,20) do (
    timeout /t 2 /nobreak >nul 2>&1
    curl -s -m 2 http://127.0.0.1:8001/health >nul 2>nul && goto :ready
)

:ready
echo   [OK] Services are up.
echo.
echo   Web    http://localhost:3000
echo   API    http://127.0.0.1:8001/docs
echo   Crawl  http://localhost:3000/collect
echo.
echo   Stop with stop.bat
echo.

start "" http://localhost:3000
exit /b 0
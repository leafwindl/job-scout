@echo off
setlocal
chcp 65001 >nul

REM ============================================================
REM  job-scout: start an isolated browser with CDP enabled.
REM  You control this browser. You log in yourself.
REM ============================================================

set "PORT=9222"
set "PROFILE=%~dp0.playwright\boss-profile"

if not exist "%PROFILE%" mkdir "%PROFILE%"

set "CHROME_A=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME_B=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "EDGE_A=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set "EDGE_B=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

set "BROWSER="
if exist "%CHROME_A%" set "BROWSER=%CHROME_A%"
if not defined BROWSER if exist "%CHROME_B%" set "BROWSER=%CHROME_B%"
if not defined BROWSER if exist "%EDGE_A%" set "BROWSER=%EDGE_A%"
if not defined BROWSER if exist "%EDGE_B%" set "BROWSER=%EDGE_B%"

if not defined BROWSER goto NOBROWSER

echo.
echo ============================================================
echo  Browser : %BROWSER%
echo  Profile : %PROFILE%
echo  CDP port: %PORT%
echo ============================================================
echo.
echo Starting browser...

start "" "%BROWSER%" --remote-debugging-port=%PORT% --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --disable-background-mode --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --start-maximized "https://www.zhipin.com/"

echo.
echo Done. In the browser window:
echo   1. Complete the security check if shown
echo   2. Log in to BOSS Zhipin
echo   3. Search "Agent" and choose your city
echo.
echo This browser uses its own profile, so your daily browser is untouched.
echo Login state is saved, so next time you won't need to log in again.
echo.
echo When ready, come back to your terminal and run:
echo   uv run job-scout collect --keyword "Agent" --city "Guangzhou"
echo.
pause
exit /b 0

:NOBROWSER
echo [ERROR] Chrome or Edge not found.
pause
exit /b 1

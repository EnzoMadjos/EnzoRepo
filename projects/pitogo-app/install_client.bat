@echo off
setlocal enabledelayedexpansion
:: ──────────────────────────────────────────────────────────────────────────────
:: PITOGO Barangay App — Client Installer (Windows)
::
:: Run on each clerk / staff PC. No Docker needed — just the app.
:: Connects to the leader PC's PostgreSQL over LAN.
:: ──────────────────────────────────────────────────────────────────────────────

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║   PITOGO Barangay App — Client Setup                 ║
echo ╚══════════════════════════════════════════════════════╝
echo.

set APP_DIR=%~dp0
if "%APP_DIR:~-1%"=="\" set APP_DIR=%APP_DIR:~0,-1%
set ENV_FILE=%APP_DIR%\.env
set VENV_DIR=%APP_DIR%\.venv

:: ── 1. Check Python ──────────────────────────────────────────────────────────
echo [ 1/5 ] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   ERROR: Python 3 is not installed.
    echo   Download from: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version') do echo   OK %%V

:: ── 2. Ask for leader IP ─────────────────────────────────────────────────────
echo [ 2/5 ] Configuring connection...
echo.

:: Check for saved leader IP
set SAVED_IP=
if exist "%APP_DIR%\secure\leader_ip.txt" (
    set /p SAVED_IP=<"%APP_DIR%\secure\leader_ip.txt"
    set SAVED_IP=!SAVED_IP: =!
)

if defined SAVED_IP (
    set /p LEADER_IP="  Leader PC IP address [!SAVED_IP!] (press Enter to use saved): "
    if not defined LEADER_IP set LEADER_IP=!SAVED_IP!
) else (
    set /p LEADER_IP="  Leader PC IP address (e.g. 192.168.1.10): "
)

if not defined LEADER_IP (
    echo   ERROR: Leader IP is required.
    pause
    exit /b 1
)
echo   OK Leader IP: %LEADER_IP%

echo.
set /p DB_PASS="  Database password (copy DB_PASS from leader .env): "
if not defined DB_PASS (
    echo   ERROR: Database password is required.
    pause
    exit /b 1
)

:: ── 3. Install dependencies ──────────────────────────────────────────────────
echo [ 3/5 ] Installing dependencies...

if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    echo   Virtual environment created
)

"%VENV_DIR%\Scripts\pip.exe" install --quiet --upgrade pip
"%VENV_DIR%\Scripts\pip.exe" install --quiet -r "%APP_DIR%\requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Dependency install failed.
    pause
    exit /b 1
)
echo   Dependencies installed

:: ── 4. Write .env ────────────────────────────────────────────────────────────
echo [ 4/5 ] Writing configuration...
if not exist "%ENV_FILE%" copy "%APP_DIR%\.env.example" "%ENV_FILE%" >nul

:: Helper: update or append a key=value in .env
:: (PowerShell used for reliable in-place editing on Windows)
for %%K in (NODE_ROLE DB_BACKEND DB_HOST DB_PORT DB_NAME DB_USER DB_PASS) do (
    if "%%K"=="NODE_ROLE"  call :upsert_env %%K client
    if "%%K"=="DB_BACKEND" call :upsert_env %%K postgres
    if "%%K"=="DB_HOST"    call :upsert_env %%K %LEADER_IP%
    if "%%K"=="DB_PORT"    call :upsert_env %%K 5432
    if "%%K"=="DB_NAME"    call :upsert_env %%K pitogo
    if "%%K"=="DB_USER"    call :upsert_env %%K pitogo
    if "%%K"=="DB_PASS"    call :upsert_env %%K %DB_PASS%
)
echo   Config written to .env

:: ── 5. Create start.bat and launch ──────────────────────────────────────────
echo [ 5/5 ] Starting Pitogo App (client mode)...

:: Write start.bat for future restarts
(
    echo @echo off
    echo cd /d "%APP_DIR%"
    echo "%VENV_DIR%\Scripts\uvicorn.exe" app:app --host 0.0.0.0 --port 8300
    echo pause
) > "%APP_DIR%\start.bat"

:: Launch app in new window
start "PITOGO App" "%VENV_DIR%\Scripts\uvicorn.exe" app:app --host 0.0.0.0 --port 8300
timeout /t 3 /nobreak >nul

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║   PITOGO App is LIVE  (Client Mode)                  ║
echo ║                                                      ║
echo ║   Browser:   http://localhost:8300                   ║
echo ║   Leader DB: %LEADER_IP%:5432
echo ║                                                      ║
echo ║   To restart later: double-click start.bat          ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause
goto :eof

:: ── Helper: update key in .env or append if missing ─────────────────────────
:upsert_env
set _KEY=%1
set _VAL=%2
findstr /C:"%_KEY%=" "%ENV_FILE%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -Command "(Get-Content '%ENV_FILE%') -replace '^%_KEY%=.*', '%_KEY%=%_VAL%' | Set-Content '%ENV_FILE%'"
) else (
    echo %_KEY%=%_VAL%>> "%ENV_FILE%"
)
goto :eof

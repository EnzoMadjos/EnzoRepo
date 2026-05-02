@echo off
setlocal enabledelayedexpansion
:: ──────────────────────────────────────────────────────────────────────────────
:: PITOGO Barangay App — Leader Installer (Windows)
::
:: Run once on the main office PC. Installs PostgreSQL + the app together.
:: Requires: Docker Desktop, Python 3.10+
:: ──────────────────────────────────────────────────────────────────────────────

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║   PITOGO Barangay App — Leader Setup                 ║
echo ╚══════════════════════════════════════════════════════╝
echo.

set APP_DIR=%~dp0
if "%APP_DIR:~-1%"=="\" set APP_DIR=%APP_DIR:~0,-1%
set ENV_FILE=%APP_DIR%\.env

:: ── 1. Check Docker ──────────────────────────────────────────────────────────
echo [ 1/6 ] Checking Docker...
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   ERROR: Docker Desktop is not installed.
    echo   Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
docker compose version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   ERROR: Docker Compose v2 is required.
    echo   Update Docker Desktop to the latest version.
    pause
    exit /b 1
)
echo   OK Docker found

:: ── 2. Check Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   ERROR: Python 3 is not installed.
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ── 3. Set up .env ───────────────────────────────────────────────────────────
echo [ 2/6 ] Setting up environment...
if not exist "%ENV_FILE%" (
    copy "%APP_DIR%\.env.example" "%ENV_FILE%" >nul
    echo   Created .env from template
)

:: Generate secure DB password using Python
for /f "delims=" %%P in ('python -c "import secrets; print(secrets.token_urlsafe(24))"') do set DB_PASS=%%P

:: Check if DB_PASS is already set
findstr /C:"DB_PASS=" "%ENV_FILE%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo DB_PASS=%DB_PASS%>> "%ENV_FILE%"
    echo   Generated secure database password
) else (
    echo   Using existing configuration
)

:: Ensure all DB vars are present (append if missing)
for %%K in (DB_BACKEND DB_HOST DB_PORT DB_NAME DB_USER NODE_ROLE) do (
    findstr /C:"%%K=" "%ENV_FILE%" >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        if "%%K"=="DB_BACKEND" echo DB_BACKEND=postgres>> "%ENV_FILE%"
        if "%%K"=="DB_HOST"    echo DB_HOST=localhost>> "%ENV_FILE%"
        if "%%K"=="DB_PORT"    echo DB_PORT=5432>> "%ENV_FILE%"
        if "%%K"=="DB_NAME"    echo DB_NAME=pitogo>> "%ENV_FILE%"
        if "%%K"=="DB_USER"    echo DB_USER=pitogo>> "%ENV_FILE%"
        if "%%K"=="NODE_ROLE"  echo NODE_ROLE=leader>> "%ENV_FILE%"
    )
)
echo   DB config written to .env

:: ── 4. Pull PostgreSQL image ─────────────────────────────────────────────────
echo [ 3/6 ] Pulling PostgreSQL 16 image...
docker pull postgres:16-alpine
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to pull PostgreSQL image. Check your internet connection.
    pause
    exit /b 1
)
echo   Image ready

:: ── 5. Start services ────────────────────────────────────────────────────────
echo [ 4/6 ] Starting PostgreSQL + Pitogo App...
cd /d "%APP_DIR%"
docker compose --profile leader up -d --build
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Docker Compose failed. Run: docker compose logs
    pause
    exit /b 1
)
echo   Containers started

:: ── 6. Wait for database ─────────────────────────────────────────────────────
echo [ 5/6 ] Waiting for database to be ready...
set WAITED=0
:wait_loop
docker compose exec -T db pg_isready -U pitogo -d pitogo >nul 2>&1
if %ERRORLEVEL% EQU 0 goto db_ready
if %WAITED% GEQ 60 (
    echo   ERROR: Database did not start in time.
    echo   Run: docker compose logs db
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
set /a WAITED=WAITED+2
goto wait_loop
:db_ready
echo   Database is ready

:: ── 7. Run migrations ────────────────────────────────────────────────────────
echo [ 6/6 ] Running database migrations...
docker compose exec -T app alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Migration failed. Check: docker compose logs app
    pause
    exit /b 1
)
echo   Database schema is up to date

:: ── Done ─────────────────────────────────────────────────────────────────────
:: Get LAN IP
set LAN_IP=
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    if not defined LAN_IP (
        set LAN_IP=%%A
        set LAN_IP=!LAN_IP: =!
    )
)
if not defined LAN_IP set LAN_IP=localhost

:: Save leader IP for reference
if not exist "%APP_DIR%\secure" mkdir "%APP_DIR%\secure"
echo %LAN_IP%> "%APP_DIR%\secure\leader_ip.txt"

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║   PITOGO App is LIVE                                 ║
echo ║                                                      ║
echo ║   Browser:  http://%LAN_IP%:8300
echo ║                                                      ║
echo ║   Client PCs: use Leader IP = %LAN_IP%
echo ╚══════════════════════════════════════════════════════╝
echo.
echo   Leader IP saved to secure\leader_ip.txt
echo.
pause

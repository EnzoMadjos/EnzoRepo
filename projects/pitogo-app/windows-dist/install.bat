@echo off
setlocal EnableDelayedExpansion

echo.
echo  ============================================================
echo   PITOGO Barangay App — Windows Installer
echo  ============================================================
echo.

:: ── Locate Python ────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Download from https://python.org/downloads
    echo          Make sure "Add Python to PATH" is checked during install.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo  Python found: %PY_VER%

:: Require Python 3.10+
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set "PY_MAJ=%%a"
    set "PY_MIN=%%b"
)
if %PY_MAJ% LSS 3 (
    echo  [ERROR] Python 3.10 or newer is required.
    pause & exit /b 1
)
if %PY_MAJ% EQU 3 if %PY_MIN% LSS 10 (
    echo  [ERROR] Python 3.10 or newer is required (found %PY_VER%).
    pause & exit /b 1
)

:: ── Determine install directory (parent of this script = project root) ────────
set "SCRIPT_DIR=%~dp0"
:: windows-dist\ sits inside project root; go up one level
pushd "%SCRIPT_DIR%.."
set "APP_DIR=%CD%"
popd

echo  Install directory: %APP_DIR%
echo.

:: ── Create virtual environment ───────────────────────────────────────────────
set "VENV=%APP_DIR%\.venv"
if exist "%VENV%\Scripts\activate.bat" (
    echo  [OK] Virtual environment already exists — skipping creation.
) else (
    echo  Creating virtual environment…
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
    echo  [OK] Virtual environment created.
)

:: ── Install / upgrade dependencies ──────────────────────────────────────────
echo.
echo  Installing Python dependencies (this may take a minute)…
"%VENV%\Scripts\pip.exe" install --upgrade pip --quiet
"%VENV%\Scripts\pip.exe" install -r "%APP_DIR%\requirements.txt" --quiet
if errorlevel 1 (
    echo.
    echo  [WARN] Some packages failed. WeasyPrint requires additional system libraries.
    echo         See windows-dist\INSTALL.md for details.
)
echo  [OK] Dependencies installed.

:: ── Run database migrations ──────────────────────────────────────────────────
echo.
echo  Applying database migrations…
pushd "%APP_DIR%"
"%VENV%\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    echo  [WARN] Migration step had issues — the app will attempt to create tables on first run.
)
popd
echo  [OK] Database ready.

:: ── Create the start shortcut / launcher ────────────────────────────────────
echo.
echo  Creating start script…
set "STARTER=%APP_DIR%\windows-dist\start_pitogo.bat"

(
echo @echo off
echo cd /d "%APP_DIR%"
echo start "" "%VENV%\Scripts\pythonw.exe" start.py
echo timeout /t 3 /nobreak ^>nul
echo start http://localhost:8300
) > "%STARTER%"

echo  [OK] Launcher written to windows-dist\start_pitogo.bat

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo   Installation complete!
echo.
echo   To start the app:
echo     windows-dist\start_pitogo.bat
echo.
echo   Or double-click start_pitogo.bat in Explorer.
echo  ============================================================
echo.
pause
endlocal

@echo off
setlocal

:: ── Locate project root (one level up from windows-dist\) ───────────────────
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "APP_DIR=%CD%"
popd

set "VENV=%APP_DIR%\.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo  [ERROR] Virtual environment not found.
    echo          Run windows-dist\install.bat first.
    pause
    exit /b 1
)

:: Launch with pythonw so no console window appears
start "" "%VENV%\Scripts\pythonw.exe" "%APP_DIR%\start.py"

:: Wait briefly then open browser
timeout /t 4 /nobreak >nul
start http://localhost:8300

endlocal

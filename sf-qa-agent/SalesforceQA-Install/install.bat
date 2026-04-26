@echo off
setlocal EnableDelayedExpansion
title SF QA Test Agent — Installer
color 0A

echo.
echo  ============================================================
echo    SF QA Test Agent  ^|  Windows Installer
echo  ============================================================
echo.
echo  This installer will:
echo    1. Verify Python 3.10+ is installed
echo    2. Create a Python virtual environment
echo    3. Install all required Python packages
echo    4. Verify Ollama is installed and pull the AI model
echo    5. Build SalesforceQA.exe from the launcher
echo    6. Create a Desktop shortcut
echo.
echo  An internet connection is required for first-time setup.
echo  The AI model download is ~2 GB — please be patient.
echo.
pause

:: -----------------------------------------------------------------------
:: Working directory = folder containing this bat
:: -----------------------------------------------------------------------
cd /d "%~dp0"
set "APP_DIR=%~dp0app"
set "DIST_DIR=%~dp0dist"

:: -----------------------------------------------------------------------
:: Step 1 — Check Python 3.10+
:: -----------------------------------------------------------------------
echo.
echo [1/6] Checking Python...

python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo  ERROR: Python was not found.
    echo.
    echo  Please install Python 3.10 or newer from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, check the box:
    echo    "Add Python to PATH"
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo    Found Python %PY_VER%

:: Extract major.minor
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if %PY_MAJOR% lss 3 (
    echo  ERROR: Python 3.10 or newer is required. You have %PY_VER%.
    pause
    exit /b 1
)
if %PY_MAJOR% equ 3 (
    if %PY_MINOR% lss 10 (
        echo  ERROR: Python 3.10 or newer is required. You have %PY_VER%.
        echo  Download the latest Python from https://www.python.org/downloads/
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo    Python OK.

:: -----------------------------------------------------------------------
:: Step 2 — Create virtual environment
:: -----------------------------------------------------------------------
echo.
echo [2/6] Creating Python virtual environment...

if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
    python -m venv "%APP_DIR%\.venv"
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo    Virtual environment created.
) else (
    echo    Virtual environment already exists.
)

set "VENV_PY=%APP_DIR%\.venv\Scripts\python.exe"
set "VENV_PIP=%APP_DIR%\.venv\Scripts\pip.exe"

:: -----------------------------------------------------------------------
:: Step 3 — Install requirements
:: -----------------------------------------------------------------------
echo.
echo [3/6] Installing Python packages (this may take a minute)...

"%VENV_PIP%" install --upgrade pip --quiet
"%VENV_PIP%" install -r "%APP_DIR%\requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo  ERROR: Package installation failed.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)

echo    Packages installed.

:: -----------------------------------------------------------------------
:: Step 4 — Check Ollama and pull model
:: -----------------------------------------------------------------------
echo.
echo [4/6] Checking Ollama...

ollama --version >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo  Ollama is not installed.
    echo.
    echo  Opening the Ollama download page...
    echo  After installing Ollama, re-run this installer.
    echo.
    start https://ollama.com/download
    pause
    exit /b 1
)

echo    Ollama found.
echo.
echo    Pulling AI model: llama3.2:3b
echo    (First time only — this is ~2 GB, please wait...)
echo.
ollama pull llama3.2:3b
if !errorlevel! neq 0 (
    echo.
    echo  WARNING: Could not pull the AI model automatically.
    echo  After setup, open a terminal and run:
    echo    ollama pull llama3.2:3b
    echo.
) else (
    echo    AI model ready.
)

:: -----------------------------------------------------------------------
:: Step 5 — Create SalesforceQA launcher batch file
:: -----------------------------------------------------------------------
echo.
echo [5/6] Creating SalesforceQA launcher...

set "LAUNCHER_BAT=%~dp0SalesforceQA-Launch.bat"

(
echo @echo off
echo title SF QA Test Agent
echo cd /d "%APP_DIR%"
echo echo Starting SF QA Test Agent...
echo echo.
echo start "" "%APP_DIR%\.venv\Scripts\pythonw.exe" -m uvicorn sf_app:app --host 0.0.0.0 --port 8200
echo timeout /t 4 /nobreak ^>nul
echo start http://localhost:8200
echo echo.
echo echo Server is running at http://localhost:8200
echo echo Keep this window open. Close it to stop the server.
echo echo.
echo pause
) > "%LAUNCHER_BAT%"

echo    Launcher created: SalesforceQA-Launch.bat

:: -----------------------------------------------------------------------
:: Step 6 — Create Desktop shortcut
:: -----------------------------------------------------------------------
echo.
echo [6/6] Creating Desktop shortcut...

set "LAUNCHER_PATH=%~dp0SalesforceQA-Launch.bat"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\SF QA Test Agent.lnk"
set "ICON_PATH=%~dp0assets\icon.ico"

:: Use PowerShell to create the shortcut
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); ^
   $s.TargetPath = '%LAUNCHER_PATH%'; ^
   $s.WorkingDirectory = '%APP_DIR%'; ^
   if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; ^
   $s.Description = 'SF QA Test Agent — AI-powered Salesforce testing'; ^
   $s.Save()"

if !errorlevel! neq 0 (
    echo  WARNING: Could not create desktop shortcut automatically.
    echo  You can manually create a shortcut to:
    echo    %EXE_PATH%
) else (
    echo    Desktop shortcut created.
)

:: -----------------------------------------------------------------------
:: Set up .env if not present
:: -----------------------------------------------------------------------
if not exist "%APP_DIR%\.env" (
    copy "%APP_DIR%\.env.example" "%APP_DIR%\.env" >nul
    echo    .env file created from template.
)

:: -----------------------------------------------------------------------
:: Done
:: -----------------------------------------------------------------------
echo.
echo  ============================================================
echo    Installation complete!
echo  ============================================================
echo.
echo  ^> Double-click "SF QA Test Agent" on your Desktop to launch.
echo    (or run SalesforceQA-Launch.bat directly from the install folder)
echo.
echo  The app opens in your browser at http://localhost:8200
echo.
echo  First launch may take 10-15 seconds while the AI model loads.
echo.
pause

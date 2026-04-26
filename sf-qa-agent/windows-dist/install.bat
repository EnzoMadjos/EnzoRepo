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
echo    1. Install Python 3.13 if not found
echo    2. Create a Python virtual environment
echo    3. Install all required Python packages
echo    4. Install Ollama and pull the AI model
echo    5. Create the launch script and app config
echo    6. Create a Desktop shortcut
echo.
echo  Internet connection required. AI model is ~2 GB.
echo  Support connection is pre-configured — no extra setup needed.
echo.
pause

:: Lock working directory to folder containing this bat
cd /d "%~dp0"
set "INSTALL_ROOT=%~dp0"
if "!INSTALL_ROOT:~-1!"=="\" set "INSTALL_ROOT=!INSTALL_ROOT:~0,-1!"
set "APP_DIR=!INSTALL_ROOT!\app"

echo.
echo    Install root: !INSTALL_ROOT!
echo    App dir:      !APP_DIR!
echo.

:: -----------------------------------------------------------------------
:: Step 1 — Python
:: -----------------------------------------------------------------------
echo [1/6] Checking Python...

set "PY_OK=0"
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%p in ('where python 2^>nul') do (
        set "PY_PATH=%%p"
        goto :check_stub
    )
)
goto :install_python

:check_stub
echo !PY_PATH! | findstr /i "WindowsApps" >nul
if !errorlevel! equ 0 goto :install_python
for /f "tokens=1,2 delims=." %%a in ('python -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2^>nul') do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if !PY_MAJOR! geq 3 if !PY_MINOR! geq 10 (
    set "PY_OK=1"
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo    Python %%v found.
    goto :python_done
)

:install_python
echo    Installing Python 3.13 via winget...
winget install Python.Python.3.13 --override "/quiet InstallAllUsers=1 PrependPath=1" --accept-source-agreements --accept-package-agreements
if !errorlevel! neq 0 (
    echo.
    echo  winget failed. Open https://www.python.org/downloads/ and install Python.
    echo  Check "Add Python to PATH" then re-run this installer.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;%PATH%"
echo    Python installed.

:python_done
echo    Python OK.

:: -----------------------------------------------------------------------
:: Step 2 — Virtual environment
:: -----------------------------------------------------------------------
echo.
echo [2/6] Creating Python virtual environment...

if not exist "!APP_DIR!" (
    echo  ERROR: app\ folder not found at !APP_DIR!
    echo  Make sure all files from the zip are present.
    pause
    exit /b 1
)

if not exist "!APP_DIR!\.venv\Scripts\python.exe" (
    python -m venv "!APP_DIR!\.venv"
    if !errorlevel! neq 0 (
        echo  ERROR: Failed to create virtual environment.
        echo  Try running as Administrator.
        pause
        exit /b 1
    )
    echo    Virtual environment created.
) else (
    echo    Virtual environment already exists — skipping.
)

set "VENV_PY=!APP_DIR!\.venv\Scripts\python.exe"
set "VENV_PIP=!APP_DIR!\.venv\Scripts\pip.exe"

:: -----------------------------------------------------------------------
:: Step 3 — Install packages
:: -----------------------------------------------------------------------
echo.
echo [3/6] Installing Python packages ^(this may take 3-5 minutes^)...
echo    Downloading and installing dependencies. Please wait ^— do not close this window.
echo.

"!VENV_PIP!" install --upgrade pip --quiet
"!VENV_PIP!" install -r "!APP_DIR!\requirements.txt" --progress-bar on
if !errorlevel! neq 0 (
    echo  ERROR: Package installation failed. Check internet connection.
    pause
    exit /b 1
)
echo    Packages installed.

:: -----------------------------------------------------------------------
:: Step 4 — Ollama
:: -----------------------------------------------------------------------
echo.
echo [4/6] Checking Ollama...

ollama --version >nul 2>&1
if !errorlevel! neq 0 (
    echo    Installing Ollama via winget...
    winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo  Opening Ollama download page. Install then re-run.
        start https://ollama.com/download
        pause
        exit /b 1
    )
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;%PATH%"
)

echo    Starting Ollama...
start /min "" ollama serve
timeout /t 3 /nobreak >nul

echo    Pulling AI model: llama3.2:3b  ^(~2 GB — please wait...^)
ollama pull llama3.2:3b
if !errorlevel! neq 0 (
    echo    WARNING: Could not pull model. Run later: ollama pull llama3.2:3b
) else (
    echo    AI model ready.
)

:: -----------------------------------------------------------------------
:: Step 5 — .env + Launcher
:: -----------------------------------------------------------------------
echo.
echo [5/6] Creating launcher...

if not exist "!APP_DIR!\.env" (
    if exist "!APP_DIR!\.env.example" copy "!APP_DIR!\.env.example" "!APP_DIR!\.env" >nul
    echo    .env created.
)

set "LAUNCHER=!INSTALL_ROOT!\SalesforceQA-Launch.bat"
(
    echo @echo off
    echo title SF QA Test Agent
    echo cd /d "!APP_DIR!"
    echo echo Starting server... keep this window open.
    echo "!VENV_PY!" -m uvicorn sf_app:app --host 0.0.0.0 --port 8200
    echo pause
) > "!LAUNCHER!"
echo    Launcher created.

:: -----------------------------------------------------------------------
:: Step 6 — Desktop shortcut (two methods)
:: -----------------------------------------------------------------------
echo.
echo [6/6] Creating Desktop shortcut...

set "SHORTCUT=%USERPROFILE%\Desktop\SF QA Test Agent.lnk"

:: Method 1 — VBScript (most reliable)
set "VBS=%TEMP%\mkshortcut_%RANDOM%.vbs"
(
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo Set s = ws.CreateShortcut^("%SHORTCUT%"^)
    echo s.TargetPath = "!LAUNCHER!"
    echo s.WorkingDirectory = "!APP_DIR!"
    echo s.Description = "SF QA Test Agent"
    echo s.Save
) > "!VBS!"
cscript //nologo "!VBS!"
del "!VBS!" >nul 2>&1

if exist "%SHORTCUT%" (
    echo    Desktop shortcut created.
) else (
    :: Method 2 — PowerShell fallback
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell;$s=$ws.CreateShortcut('!SHORTCUT!');$s.TargetPath='!LAUNCHER!';$s.WorkingDirectory='!APP_DIR!';$s.Save()"
    if exist "%SHORTCUT%" (
        echo    Desktop shortcut created via PowerShell.
    ) else (
        echo    WARNING: Could not create shortcut automatically.
        echo    Right-click SalesforceQA-Launch.bat -> Send to -> Desktop ^(shortcut^)
    )
)

:: -----------------------------------------------------------------------
:: Done
:: -----------------------------------------------------------------------
echo.
echo  ============================================================
echo    Installation complete!
echo  ============================================================
echo.
echo  Double-click "SF QA Test Agent" on your Desktop to launch.
echo  The app opens at http://localhost:8200
echo.
echo  In the app, click "Admin" to see the support connection status.
echo  When your admin is online you can send error logs or receive updates
echo  directly from inside the app.
echo.
pause

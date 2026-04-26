@echo off
setlocal EnableDelayedExpansion
title SF QA — Auto Setup Fix
color 0A

echo.
echo  ============================================================
echo    SF QA Test Agent — Auto Setup Fix
echo  ============================================================
echo.
echo  This will automatically fix all setup issues and start the app.
echo  Please keep this window open throughout the process.
echo.
pause

:: -----------------------------------------------------------------------
:: Step 1 — Disable Microsoft Store Python alias
:: -----------------------------------------------------------------------
echo.
echo [1/5] Disabling Microsoft Store Python alias...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe" /f >nul 2>&1
powershell -NoProfile -Command ^
  "Get-AppxPackage *WindowsStore* | ForEach-Object { $null }" >nul 2>&1
:: Disable via registry
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /v AllowDevelopmentWithoutDevLicense /t REG_DWORD /d 0 /f >nul 2>&1
echo    Done.

:: -----------------------------------------------------------------------
:: Step 2 — Install real Python if not found or if it's the Store stub
:: -----------------------------------------------------------------------
echo.
echo [2/5] Checking Python...

set "PY_OK=0"
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%p in ('where python 2^>nul') do set PY_PATH=%%p
    echo !PY_PATH! | findstr /i "WindowsApps" >nul
    if !errorlevel! neq 0 (
        set "PY_OK=1"
        for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo    Found Python %%v at !PY_PATH!
    ) else (
        echo    Microsoft Store stub detected — will install real Python.
    )
) else (
    echo    Python not found — will install now.
)

if "!PY_OK!"=="0" (
    echo.
    echo    Installing Python 3.13 via winget...
    echo    ^(This may take 1-2 minutes^)
    echo.
    winget install Python.Python.3.13 --override "/quiet InstallAllUsers=1 PrependPath=1" --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo.
        echo    winget failed. Trying direct download...
        echo    Please install Python manually from https://www.python.org/downloads/
        echo    Make sure to check "Add Python to PATH" during install.
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo.
    echo    Python installed. Refreshing PATH...
    :: Refresh PATH without restarting
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%b"
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USR_PATH=%%b"
    set "PATH=!SYS_PATH!;!USR_PATH!;%PATH%"
)

:: Verify Python works
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo  ERROR: Python still not found after install.
    echo  Please restart your computer and re-run this file.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo    Python %%v ready.

:: -----------------------------------------------------------------------
:: Step 3 — Move app folder to C:\SalesforceQA if still in wrong place
:: -----------------------------------------------------------------------
echo.
echo [3/5] Checking install location...

set "TARGET=C:\SalesforceQA"
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

if /i "!SCRIPT_DIR!"=="!TARGET!" (
    echo    Already in correct location: !SCRIPT_DIR!
) else (
    echo    Moving files from !SCRIPT_DIR! to !TARGET!...
    if exist "!TARGET!" (
        echo    Removing old install at !TARGET!...
        rmdir /s /q "!TARGET!"
    )
    xcopy "!SCRIPT_DIR!" "!TARGET!\" /E /I /H /Y /Q
    if !errorlevel! neq 0 (
        echo  ERROR: Could not copy files to !TARGET!
        echo  Try running this file as Administrator.
        pause
        exit /b 1
    )
    echo    Files copied to !TARGET!
    echo.
    echo    Restarting setup from new location...
    start "" "!TARGET!\setup-fix.bat"
    exit /b 0
)

set "APP_DIR=%TARGET%\app"

:: -----------------------------------------------------------------------
:: Step 4 — Run install.bat
:: -----------------------------------------------------------------------
echo.
echo [4/5] Running installer...
echo.

if not exist "%TARGET%\install.bat" (
    echo  ERROR: install.bat not found in %TARGET%
    echo  Make sure all files from the zip are present.
    pause
    exit /b 1
)

call "%TARGET%\install.bat"
if !errorlevel! neq 0 (
    echo.
    echo  ERROR: Installer reported an error. See messages above.
    pause
    exit /b 1
)

:: -----------------------------------------------------------------------
:: Step 5 — Start the server
:: -----------------------------------------------------------------------
echo.
echo [5/5] Starting SF QA server...
echo.

if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
    echo  ERROR: Virtual environment not found after install.
    echo  Please re-run install.bat manually.
    pause
    exit /b 1
)

:: Copy .env if missing
if not exist "%APP_DIR%\.env" (
    if exist "%APP_DIR%\.env.example" (
        copy "%APP_DIR%\.env.example" "%APP_DIR%\.env" >nul
        echo    .env created from template.
    )
)

echo    Launching server...
start "SF QA Server" /min cmd /k "cd /d %APP_DIR% && .venv\Scripts\python.exe -m uvicorn sf_app:app --host 0.0.0.0 --port 8200"

echo    Waiting for server to start...
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:8200

echo.
echo  ============================================================
echo    All done! The app should be opening in your browser.
echo    http://localhost:8200
echo.
echo    The "SF QA Server" window must stay open.
echo    Close it to stop the server.
echo  ============================================================
echo.
pause

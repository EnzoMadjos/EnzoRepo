@echo off
setlocal EnableDelayedExpansion
title SF QA Test Agent — Diagnostics
color 0E

set "REPORT=%USERPROFILE%\Desktop\sfqa-debug-report.txt"
set "APP_DIR=%~dp0app"
set "VENV_PY=%APP_DIR%\.venv\Scripts\python.exe"

echo Running diagnostics... please wait.
echo.

(
echo ============================================================
echo  SF QA Test Agent — Debug Report
echo  Generated: %DATE% %TIME%
echo  Machine:   %COMPUTERNAME%
echo  User:      %USERNAME%
echo ============================================================
echo.

:: -----------------------------------------------------------------------
echo [1] Python
echo -----------------------------------------------------------------------
python --version 2>&1
where python 2>&1
for /f "tokens=*" %%p in ('where python 2^>nul') do set PY_PATH=%%p
echo %PY_PATH% | findstr /i "WindowsApps" >nul
if !errorlevel! equ 0 (
    echo WARNING: Microsoft Store Python stub detected - this cannot create venvs!
    echo Fix: Start Menu ^> Manage App Execution Aliases ^> turn OFF python.exe
    echo Then install real Python from https://www.python.org/downloads/
) else (
    echo Python path looks OK.
)
echo.

:: -----------------------------------------------------------------------
echo [2] Virtual Environment
echo -----------------------------------------------------------------------
if exist "%VENV_PY%" (
    echo FOUND: %VENV_PY%
    "%VENV_PY%" --version 2>&1
) else (
    echo NOT FOUND: %VENV_PY%
    echo Please re-run install.bat
)
echo.

:: -----------------------------------------------------------------------
echo [3] Installed Python Packages
echo -----------------------------------------------------------------------
if exist "%VENV_PY%" (
    "%APP_DIR%\.venv\Scripts\pip.exe" list 2>&1
) else (
    echo Skipped — venv not found
)
echo.

:: -----------------------------------------------------------------------
echo [4] Ollama
echo -----------------------------------------------------------------------
ollama --version 2>&1
ollama list 2>&1
echo.
echo Ollama service status:
curl -s http://localhost:11434 2>&1
echo.

:: -----------------------------------------------------------------------
echo [5] App Server
echo -----------------------------------------------------------------------
echo Checking http://localhost:8200 ...
curl -s -o nul -w "HTTP Status: %%{http_code}" http://localhost:8200 2>&1
echo.
curl -s http://localhost:8200 2>&1 | findstr /i "SF QA html title" 2>&1
echo.

:: -----------------------------------------------------------------------
echo [6] App Files
echo -----------------------------------------------------------------------
echo APP_DIR: %APP_DIR%
echo.
if exist "%APP_DIR%" (
    dir "%APP_DIR%" /b 2>&1
) else (
    echo APP_DIR not found!
)
echo.
if exist "%APP_DIR%\templates\qa.html" (
    echo templates\qa.html: FOUND
) else (
    echo templates\qa.html: MISSING
)
echo.

:: -----------------------------------------------------------------------
echo [7] App Log
echo -----------------------------------------------------------------------
if exist "%APP_DIR%\secure\app.log" (
    echo Last 60 lines of app.log:
    echo.
    powershell -NoProfile -Command "Get-Content '%APP_DIR%\secure\app.log' -Tail 60" 2>&1
) else (
    echo app.log not found — server may not have run yet or log not created.
)
echo.

:: -----------------------------------------------------------------------
echo [8] Network Ports
echo -----------------------------------------------------------------------
echo Checking port 8200:
netstat -ano | findstr ":8200" 2>&1
echo.
echo Checking port 11434 ^(Ollama^):
netstat -ano | findstr ":11434" 2>&1
echo.

:: -----------------------------------------------------------------------
echo [9] .env File
echo -----------------------------------------------------------------------
if exist "%APP_DIR%\.env" (
    echo .env EXISTS — contents ^(credentials hidden^):
    type "%APP_DIR%\.env" 2>&1
) else (
    echo .env NOT FOUND — copy .env.example to .env in the app folder
)
echo.

:: -----------------------------------------------------------------------
echo [10] Windows and System Info
echo -----------------------------------------------------------------------
ver
echo.
systeminfo | findstr /i "OS Name OS Version Total Physical"
echo.

echo ============================================================
echo  End of Report
echo ============================================================
) > "%REPORT%" 2>&1

echo.
echo ============================================================
echo  Diagnostics complete!
echo ============================================================
echo.
echo  Report saved to your Desktop:
echo  sfqa-debug-report.txt
echo.
echo  Please send that file to your administrator.
echo.
start "" "%USERPROFILE%\Desktop"
pause

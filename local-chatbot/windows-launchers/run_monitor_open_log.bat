@echo off
REM NITRO — Run Integrity Monitor + Open Log
REM Checks NITRO secure files and opens the result in Notepad.

set LOGDIR=%~dp0logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set LOGFILE=%LOGDIR%\nitro_monitor.txt

echo Running NITRO integrity monitor... > "%LOGFILE%"
echo. >> "%LOGFILE%"

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed. >> "%LOGFILE%"
    echo Please run: python3 nitro_monitor.py from the WSL terminal. >> "%LOGFILE%"
) else (
    wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && python3 nitro_monitor.py" >> "%LOGFILE%" 2>&1
)

echo. >> "%LOGFILE%"
echo Monitor finished.
start "" notepad.exe "%LOGFILE%"
echo.
echo Press any key to close.
pause >nul

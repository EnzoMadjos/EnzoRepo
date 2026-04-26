@echo off
REM NITRO — Run Integrity Monitor (Timestamped History)
REM Saves a new dated log file every run so you keep history.

set LOGDIR=%~dp0logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f "tokens=1-3 delims=/" %%A in ("%date%") do set D=%%C-%%A-%%B
for /f "tokens=1-2 delims=:" %%A in ("%time%") do set T=%%A-%%B
set T=%T: =0%
set LOGFILE=%LOGDIR%\nitro_monitor_%D%_%T%.txt

echo Running NITRO integrity monitor... > "%LOGFILE%"
echo. >> "%LOGFILE%"

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed. >> "%LOGFILE%"
    echo Please run: python3 nitro_monitor.py from the WSL terminal. >> "%LOGFILE%"
) else (
    wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && python3 nitro_monitor.py" >> "%LOGFILE%" 2>&1
)

echo. >> "%LOGFILE%"
echo Monitor finished. Log saved to: %LOGFILE%
start "" notepad.exe "%LOGFILE%"
echo.
echo Press any key to close.
pause >nul

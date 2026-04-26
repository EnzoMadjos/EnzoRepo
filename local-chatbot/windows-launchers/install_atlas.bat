@echo off
REM ATLAS — Run Install Script (Windows Launcher)
REM Double-click this ONCE on a new computer to set everything up.

echo ============================================
echo   ATLAS — First-Time Installation
echo ============================================
echo.

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed on this computer.
    echo         Please install WSL2 first: https://aka.ms/wsl2
    pause
    exit /b 1
)

wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && bash install.sh"

echo.
echo Press any key to close this window.
pause >nul

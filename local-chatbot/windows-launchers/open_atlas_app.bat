@echo off
REM ATLAS Desktop App — Opens ATLAS as a standalone window (no browser needed)

echo ============================================
echo   ATLAS — Launching Desktop App...
echo ============================================
echo.

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed.
    pause
    exit /b 1
)

wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && venv/bin/python atlas_app_win.py"

pause

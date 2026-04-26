@echo off
REM ATLAS — Main Launcher (Windows)
REM Double-click to start ATLAS on port 8200

echo ============================================
echo   ATLAS — AI Assistant
echo   Starting on http://localhost:8200
echo ============================================
echo.

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed.
    echo Please install WSL2: https://aka.ms/wsl2
    pause
    exit /b 1
)

REM Start the server in WSL
echo [*] Starting server...
wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && venv/bin/uvicorn app:app --host 127.0.0.1 --port 8200"

pause

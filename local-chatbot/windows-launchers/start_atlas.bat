@echo off
REM ATLAS — Start Server (Windows Launcher)
REM Double-click this to launch the ATLAS AI assistant from Windows via WSL.

echo ============================================
echo   ATLAS — Starting AI Assistant...
echo ============================================
echo.

if not exist "%windir%\system32\wsl.exe" (
    echo [ERROR] WSL is not installed on this computer.
    echo         Please install WSL2 first: https://aka.ms/wsl2
    pause
    exit /b 1
)

wsl.exe -e bash -lc "cd /home/enzo/ai-lab/local-chatbot && bash start_atlas.sh"

echo.
echo Press any key to close this window.
pause >nul

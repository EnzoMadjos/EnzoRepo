@echo off
REM ATLAS — Build Windows .exe
REM Run this once to generate ATLAS.exe in the dist\ folder.

setlocal
set PYTHON=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe
set ROOT=%~dp0

echo ============================================
echo   ATLAS — Building Desktop App (.exe)
echo ============================================
echo.

REM Confirm Python exists
if not exist "%PYTHON%" (
    echo [ERROR] Windows Python not found at:
    echo         %PYTHON%
    echo.
    echo Edit this file and set the PYTHON variable to your Python path.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
"%PYTHON%" -m pip install pywebview pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/3] Building ATLAS.exe...
pushd "%ROOT%\.."
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name ATLAS ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    atlas_app_win.py

if errorlevel 1 (
    popd
    echo.
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)
popd
echo       Done.
echo.

echo [3/3] Cleaning up build files...
pushd "%ROOT%\.."
if exist build rmdir /s /q build
if exist ATLAS.spec del /q ATLAS.spec
popd
echo       Done.
echo.

echo ============================================
echo   SUCCESS! ATLAS.exe is in:
echo   %ROOT%..\dist\ATLAS.exe
echo ============================================
echo.
echo Double-click dist\ATLAS.exe to launch ATLAS.
echo.
pause

@echo off
setlocal EnableDelayedExpansion
title SF QA Test Agent — Update
color 0B

cd /d "%~dp0"
set "UPDATE_DIR=%~dp0"
if "!UPDATE_DIR:~-1!"=="\" set "UPDATE_DIR=!UPDATE_DIR:~0,-1!"

:: Find app folder — same logic as install.bat
:: update.bat lives alongside the app folder (one level up or same folder)
if exist "!UPDATE_DIR!\app\sf_app.py" (
    set "APP_DIR=!UPDATE_DIR!\app"
) else if exist "!UPDATE_DIR!\sf_app.py" (
    set "APP_DIR=!UPDATE_DIR!"
) else (
    echo.
    echo  ERROR: Could not locate the app folder.
    echo  Make sure update.bat is in the same folder as the app\ directory.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    SF QA Test Agent  ^|  Updater
echo  ============================================================
echo.
echo  App folder : !APP_DIR!
echo.
echo  This will update:
echo    - sf_app.py
echo    - templates\qa.html
echo.
echo  Your org profiles and settings will NOT be affected.
echo.
pause

set "FILES_DIR=!UPDATE_DIR!\update_files"

if not exist "!FILES_DIR!\sf_app.py" (
    echo  ERROR: update_files\sf_app.py not found.
    echo  Make sure the update_files folder is next to update.bat.
    pause
    exit /b 1
)
if not exist "!FILES_DIR!\qa.html" (
    echo  ERROR: update_files\qa.html not found.
    pause
    exit /b 1
)

echo.
echo  [1/2] Updating sf_app.py ...
copy /Y "!FILES_DIR!\sf_app.py" "!APP_DIR!\sf_app.py" >nul
if !errorlevel! neq 0 (
    echo  ERROR: Failed to copy sf_app.py — is the app currently running?
    echo  Please close the app and try again.
    pause
    exit /b 1
)
echo         OK

echo  [2/2] Updating templates\qa.html ...
copy /Y "!FILES_DIR!\qa.html" "!APP_DIR!\templates\qa.html" >nul
if !errorlevel! neq 0 (
    echo  ERROR: Failed to copy qa.html
    pause
    exit /b 1
)
echo         OK

echo.
echo  ============================================================
echo    Update complete!
echo    Please restart the app (double-click the desktop shortcut).
echo  ============================================================
echo.
pause

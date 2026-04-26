@echo off
setlocal EnableDelayedExpansion
title SF QA Test Agent — Quick Patch
color 0B

echo.
echo  ============================================================
echo    SF QA Test Agent  ^|  Quick Patch
echo  ============================================================
echo.

:: -----------------------------------------------------------------------
:: Find the app folder
:: -----------------------------------------------------------------------
set "APP_DIR="

if exist "%~dp0app\sf_app.py"         set "APP_DIR=%~dp0app"

if "!APP_DIR!"=="" if exist "%USERPROFILE%\Desktop\sf-qa-agent-windows\app\sf_app.py" (
    set "APP_DIR=%USERPROFILE%\Desktop\sf-qa-agent-windows\app"
)
if "!APP_DIR!"=="" if exist "%USERPROFILE%\Downloads\sf-qa-agent-windows\app\sf_app.py" (
    set "APP_DIR=%USERPROFILE%\Downloads\sf-qa-agent-windows\app"
)
if "!APP_DIR!"=="" if exist "C:\SalesforceQA\SalesforceQA-Install\app\sf_app.py" (
    set "APP_DIR=C:\SalesforceQA\SalesforceQA-Install\app"
)
if "!APP_DIR!"=="" if exist "C:\sf-qa-agent\app\sf_app.py" (
    set "APP_DIR=C:\sf-qa-agent\app"
)

if "!APP_DIR!"=="" (
    echo  Could not find the app automatically.
    echo  Please enter the full path to the app folder.
    echo  (This is the folder that contains sf_app.py)
    echo.
    set /p "APP_DIR=  App folder path: "
    if not exist "!APP_DIR!\sf_app.py" (
        echo.
        echo  ERROR: sf_app.py not found at !APP_DIR!
        echo  Patch aborted.
        pause
        exit /b 1
    )
)

echo  Found app at: !APP_DIR!
echo.

:: -----------------------------------------------------------------------
:: Find Python
:: -----------------------------------------------------------------------
set "PY="
if exist "!APP_DIR!\.venv\Scripts\python.exe" set "PY=!APP_DIR!\.venv\Scripts\python.exe"
if "!PY!"=="" (
    python --version >nul 2>&1
    if !errorlevel! equ 0 set "PY=python"
)
if "!PY!"=="" (
    echo  ERROR: Python not found. Please run install.bat first.
    pause
    exit /b 1
)

:: -----------------------------------------------------------------------
:: Write the patch script to a temp file then run it
:: -----------------------------------------------------------------------
echo  Applying patch...
echo.

set "TMPPY=%TEMP%\sfqa_patch_%RANDOM%.py"

> "!TMPPY!" echo APP_DIR = r"!APP_DIR!"
>> "!TMPPY!" echo.
>> "!TMPPY!" echo # Patch 1 - add missing httpx import to sf_app.py
>> "!TMPPY!" echo f1 = APP_DIR + r"\sf_app.py"
>> "!TMPPY!" echo src = open(f1, encoding="utf-8").read()
>> "!TMPPY!" echo if "import httpx" not in src:
>> "!TMPPY!" echo     src = src.replace("import auth\n", "import httpx\nimport auth\n", 1)
>> "!TMPPY!" echo     open(f1, "w", encoding="utf-8").write(src)
>> "!TMPPY!" echo     print("  [1/2] sf_app.py        patched OK")
>> "!TMPPY!" echo else:
>> "!TMPPY!" echo     print("  [1/2] sf_app.py        already up to date")
>> "!TMPPY!" echo.
>> "!TMPPY!" echo # Patch 2 - fix invisible input text color in qa.html
>> "!TMPPY!" echo f2 = APP_DIR + r"\templates\qa.html"
>> "!TMPPY!" echo src2 = open(f2, encoding="utf-8").read()
>> "!TMPPY!" echo orig = src2
>> "!TMPPY!" echo OLD = "color:var(--text)"
>> "!TMPPY!" echo NEW = "color:#111"
>> "!TMPPY!" echo def fix_input(s, input_id):
>> "!TMPPY!" echo     marker = 'id="' + input_id + '"'
>> "!TMPPY!" echo     idx = s.find(marker)
>> "!TMPPY!" echo     if idx == -1:
>> "!TMPPY!" echo         return s
>> "!TMPPY!" echo     end = s.find("/>", idx)
>> "!TMPPY!" echo     if end == -1:
>> "!TMPPY!" echo         return s
>> "!TMPPY!" echo     tag = s[idx:end+2]
>> "!TMPPY!" echo     return s[:idx] + tag.replace(OLD, NEW) + s[end+2:]
>> "!TMPPY!" echo src2 = fix_input(src2, "relay-url-input")
>> "!TMPPY!" echo src2 = fix_input(src2, "log-report-note")
>> "!TMPPY!" echo if src2 != orig:
>> "!TMPPY!" echo     open(f2, "w", encoding="utf-8").write(src2)
>> "!TMPPY!" echo     print("  [2/2] templates/qa.html patched OK")
>> "!TMPPY!" echo else:
>> "!TMPPY!" echo     print("  [2/2] templates/qa.html already up to date")

"!PY!" "!TMPPY!"
set "RC=!errorlevel!"
del "!TMPPY!" >nul 2>&1

if !RC! neq 0 (
    echo.
    echo  ERROR: Patch failed. Please contact support.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    Patch applied! Please restart the app.
echo  ============================================================
echo.
pause

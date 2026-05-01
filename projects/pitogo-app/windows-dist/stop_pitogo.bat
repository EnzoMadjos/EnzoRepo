@echo off
:: Stop any running PITOGO uvicorn process
taskkill /F /FI "WINDOWTITLE eq PITOGO*" /T >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8300 "') do (
    taskkill /F /PID %%p >nul 2>&1
)
echo  PITOGO Barangay App stopped (port 8300 released).
timeout /t 2 /nobreak >nul

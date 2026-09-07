@echo off
setlocal

echo ==========================================
echo   Porca MaDovbyk AI - Chiusura Dashboard
echo ==========================================

echo.
echo Cerco il processo Streamlit sulla porta 8501...
set FOUND=0

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    set FOUND=1
    echo Chiudo processo PID %%P...
    taskkill /PID %%P /F >nul 2>&1
)

if "%FOUND%"=="0" (
    echo Nessuna Dashboard attiva trovata.
) else (
    echo Dashboard chiusa.
)

timeout /t 2 >nul
endlocal

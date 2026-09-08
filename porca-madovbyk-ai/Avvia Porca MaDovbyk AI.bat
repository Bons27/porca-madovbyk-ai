@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Porca MaDovbyk AI

set "PORT=8501"
set "APP_URL=http://localhost:%PORT%"

echo ==========================================
echo   Porca MaDovbyk AI - Dashboard V5.1 STABILE
echo ==========================================
echo.

REM Se la Dashboard e gia attiva, non riavviare tutto: apri solo il browser.
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo Dashboard gia attiva. Apro il browser...
    start "" "%APP_URL%"
    goto :end
)

REM Individua Python solo se serve creare l'ambiente virtuale.
set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    if not defined PYTHON_CMD goto :python_missing
    echo Primo avvio: preparo l'ambiente Python...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

REM Installa/aggiorna le dipendenze solo se requirements.txt e cambiato
REM oppure se manca una dipendenza fondamentale.
set "REQ_HASH="
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 'requirements.txt').Hash" 2^>nul') do set "REQ_HASH=%%H"

set "NEED_DEPS=0"
if not exist ".venv\requirements.sha256" set "NEED_DEPS=1"
if defined REQ_HASH if exist ".venv\requirements.sha256" (
    set /p OLD_REQ_HASH=<".venv\requirements.sha256"
    if /I not "%REQ_HASH%"=="%OLD_REQ_HASH%" set "NEED_DEPS=1"
)

".venv\Scripts\python.exe" -c "import requests, bs4, streamlit" >nul 2>&1
if errorlevel 1 set "NEED_DEPS=1"

if "%NEED_DEPS%"=="1" (
    echo Verifico/aggiorno le dipendenze...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check -q
    if errorlevel 1 goto :error
    if defined REQ_HASH >".venv\requirements.sha256" echo %REQ_HASH%
) else (
    echo Dipendenze OK.
)

echo Preparo Dashboard V5.1 stabile...
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "_app_runtime_v5.py" del /q "_app_runtime_v5.py"

".venv\Scripts\python.exe" -m src.build_dashboard_v5
if errorlevel 1 goto :error

".venv\Scripts\python.exe" -m py_compile _app_runtime_v5.py
if errorlevel 1 goto :error

".venv\Scripts\python.exe" -c "from src.decision_fia import player_fia, fia_decision_score; print('Motori V5.1: OK')"
if errorlevel 1 goto :error

echo.
echo Dashboard pronta.
echo PC:      %APP_URL%
echo Telefono: stessa rete Wi-Fi, usa l'indirizzo Network URL mostrato qui sotto.
echo.
echo Avvio Porca MaDovbyk AI...
start "" "%APP_URL%"

REM 0.0.0.0 rende la Dashboard raggiungibile anche dagli altri dispositivi
REM della stessa rete locale. Non effettua alcuna esposizione pubblica su Internet.
".venv\Scripts\python.exe" -m streamlit run _app_runtime_v5.py --server.port %PORT% --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
if errorlevel 1 goto :error

goto :end

:python_missing
echo.
echo ERRORE: Python non trovato sul PC.
echo Installa Python oppure verifica che il comando py/python sia disponibile.
pause
exit /b 1

:error
echo.
echo ERRORE: Porca MaDovbyk AI non e riuscita ad avviarsi.
echo Copia o fotografa le ultime righe mostrate qui sopra.
pause
exit /b 1

:end
endlocal

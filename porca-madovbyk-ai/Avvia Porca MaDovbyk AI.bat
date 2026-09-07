@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Porca MaDovbyk AI - Dashboard V4 + FIA V3
echo ==========================================

where git >nul 2>&1
if %errorlevel%==0 (
    echo.
    echo Sincronizzo il progetto da GitHub...
    git -C "%~dp0.." pull --ff-only
    echo.
) else (
    echo.
    echo Git non trovato nel PATH: salto la sincronizzazione automatica.
    echo Puoi aggiornare il progetto con GitHub Desktop.
    echo.
)

where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo Primo avvio: creo l'ambiente Python...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error

    echo.
    echo Installo le dipendenze iniziali...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error

    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
) else (
    echo Ambiente Python trovato.
    echo Verifico le dipendenze...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check -q
    if errorlevel 1 goto :error
)

echo.
echo Avvio Porca MaDovbyk AI V4 con FIA V3...
start "" http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app_fia_v3.py --server.port 8501

goto :end

:error
echo.
echo ERRORE: non sono riuscito ad avviare la dashboard.
echo Controlla Python, connessione internet e dipendenze.
pause

:end
endlocal

@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Porca MaDovbyk AI - Avvio Dashboard

echo ==========================================

where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Primo avvio: creo l'ambiente Python...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

echo.
echo Aggiorno le dipendenze...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Avvio Porca MaDovbyk AI...
start "" http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501

goto :end

:error
echo.
echo ERRORE: non sono riuscito ad avviare la dashboard.
echo Controlla che Python sia installato sul PC.
pause

:end
endlocal

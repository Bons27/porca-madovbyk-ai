@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Porca MaDovbyk AI - Dashboard V5.2 + FIA Spiegabile
echo ==========================================

where git >nul 2>&1
if %errorlevel%==0 (
    echo.
    echo Sincronizzo il progetto da GitHub...
    git -C "%~dp0.." pull --ff-only
    if errorlevel 1 goto :sync_error
    echo.
) else (
    echo.
    echo Git non trovato nel PATH: salto la sincronizzazione automatica.
    echo Prima dell'avvio assicurati di aver fatto Fetch origin e Pull origin con GitHub Desktop.
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
echo Preparo Dashboard V5.2 e FIA spiegabile...
".venv\Scripts\python.exe" -m src.build_dashboard_v5
if errorlevel 1 goto :error

echo Verifico motori FIA...
".venv\Scripts\python.exe" -m py_compile _app_runtime_v5.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\fia_coach_dashboard.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\player_context_v3.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\decision_fia.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\decision_explainable_reports.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\explainable_reports_v52.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\control_center_explainable.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\repair_report_explainable.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\text_enrichment.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\start_score.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\trade_value.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\talent_scout_fia.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\talent_scout_report_fia.py
if errorlevel 1 goto :error

REM py_compile controlla solo la sintassi: questo test verifica anche gli import reali.
".venv\Scripts\python.exe" -c "from src.decision_fia import fia_start_score_delta, fia_trade_value_delta, fia_scout_score_delta; from src.decision_explainable_reports import build_formation_report, build_trade_report; print('FIA V5.2 import check: OK')"
if errorlevel 1 goto :stale_code

echo.
echo Avvio Porca MaDovbyk AI V5.2...
start "" http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run _app_runtime_v5.py --server.port 8501

goto :end

:sync_error
echo.
echo ERRORE DI SINCRONIZZAZIONE.
echo Il pull automatico da GitHub non e riuscito.
echo Apri GitHub Desktop, seleziona porca-madovbyk-ai, fai Fetch origin e poi Pull origin.
echo Se GitHub Desktop segnala modifiche locali o conflitti, non avviare la dashboard finche non sono risolti.
pause
goto :end

:stale_code
echo.
echo CODICE LOCALE NON AGGIORNATO.
echo Manca almeno una funzione FIA V5.2 richiesta dalla dashboard.
echo Apri GitHub Desktop, fai Fetch origin e Pull origin, poi rilancia questo file BAT.
pause
goto :end

:error
echo.
echo ERRORE: non sono riuscito ad avviare la Dashboard V5.2.
echo Controlla le righe sopra per il dettaglio dell'errore.
pause

:end
endlocal

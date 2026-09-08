@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Porca MaDovbyk AI - Dashboard V5.1 STABILE
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
echo Chiudo eventuale vecchia Dashboard sulla porta 8501...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)

echo Pulisco la cache Python locale...
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "_app_runtime_v5.py" del /q "_app_runtime_v5.py"

echo.
echo Preparo Dashboard V5.1 stabile + Tipster Bons...
".venv\Scripts\python.exe" -m src.build_dashboard_v5_tipster
if errorlevel 1 goto :error

echo Verifico Dashboard V5.1...
".venv\Scripts\python.exe" -m py_compile _app_runtime_v5.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\fia_coach_dashboard.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\player_context_v3.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\decision_fia.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\start_score.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\trade_value.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\tipster_bons.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\tipster_bons_dashboard.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m py_compile src\build_dashboard_v5_tipster.py
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -c "from src.decision_fia import player_fia, fia_decision_score; print('FIA V5.1 core check: OK')"
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -c "from src.tipster_bons import model_probabilities; p=model_probabilities(1.4,1.1); assert abs(p['home_win']+p['draw']+p['away_win']-1)<0.001; print('Tipster Bons core check: OK')"
if errorlevel 1 goto :error

echo.
echo Avvio Porca MaDovbyk AI V5.1...
start "" http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run _app_runtime_v5.py --server.port 8501

goto :end

:sync_error
echo.
echo ERRORE DI SINCRONIZZAZIONE.
echo Il pull automatico da GitHub non e riuscito.
echo Apri GitHub Desktop, fai Fetch origin e Pull origin, poi rilancia il BAT.
pause
goto :end

:error
echo.
echo ERRORE: avvio Dashboard V5.1 non riuscito.
echo Copia o fotografa le ultime righe mostrate qui sopra.
pause

:end
endlocal

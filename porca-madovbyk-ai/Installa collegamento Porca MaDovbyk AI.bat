@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Porca MaDovbyk AI - Installa collegamento

set "VBS_PATH=%~dp0Porca MaDovbyk AI.vbs"
set "CLOSE_PATH=%~dp0Chiudi Porca MaDovbyk AI.bat"

if not exist "%VBS_PATH%" (
    echo ERRORE: launcher VBS non trovato.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$s=$ws.CreateShortcut((Join-Path $desktop 'Porca MaDovbyk AI.lnk'));" ^
  "$s.TargetPath=Join-Path $env:WINDIR 'System32\wscript.exe';" ^
  "$s.Arguments='\"%VBS_PATH%\"';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.Description='Avvia Porca MaDovbyk AI';" ^
  "$s.Save();"

if errorlevel 1 (
    echo ERRORE: non sono riuscito a creare il collegamento sul Desktop.
    pause
    exit /b 1
)

if exist "%CLOSE_PATH%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$desktop=[Environment]::GetFolderPath('Desktop');" ^
      "$ws=New-Object -ComObject WScript.Shell;" ^
      "$s=$ws.CreateShortcut((Join-Path $desktop 'Chiudi Porca MaDovbyk AI.lnk'));" ^
      "$s.TargetPath='%CLOSE_PATH%';" ^
      "$s.WorkingDirectory='%~dp0';" ^
      "$s.Description='Chiudi Porca MaDovbyk AI';" ^
      "$s.Save();"
)

echo.
echo Collegamenti creati sul Desktop.
echo Da ora puoi usare semplicemente "Porca MaDovbyk AI".
echo.
pause
endlocal

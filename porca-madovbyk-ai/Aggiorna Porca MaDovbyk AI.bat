@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "REPO_ROOT=%~dp0.."
set "GIT_EXE="

REM 1) Git gia disponibile nel PATH.
for /f "delims=" %%G in ('where git 2^>nul') do if not defined GIT_EXE set "GIT_EXE=%%G"

REM 2) Fallback: Git incluso in GitHub Desktop.
if not defined GIT_EXE (
    for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do (
        if exist "%%~fD\resources\app\git\cmd\git.exe" set "GIT_EXE=%%~fD\resources\app\git\cmd\git.exe"
    )
)

if not defined GIT_EXE (
    exit /b 2
)

"%GIT_EXE%" -C "%REPO_ROOT%" pull --ff-only >nul 2>&1
if errorlevel 1 exit /b 1

exit /b 0

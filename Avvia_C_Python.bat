@echo off
setlocal EnableExtensions
title C Python
cd /d "%~dp0"

set "CPYTHON_HOME=%~dp0"
set "CPYTHON_HOME=%CPYTHON_HOME:~0,-1%"

REM Crea/aggiorna collegamento con logo.png -> logo.ico
if exist "%CPYTHON_HOME%\logo.ico" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\crea_collegamento.ps1" -CPythonHome "%CPYTHON_HOME%" >nul 2>&1
)

where code >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRORE] Visual Studio Code non trovato nel PATH.
    echo Installa VS Code da https://code.visualstudio.com/
    echo e assicurati che "code" sia nel PATH.
    echo.
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRORE] Python non trovato nel PATH.
    echo Installa Python 3 e riprova.
    echo.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo   C Python
echo   interprete + editor
echo  ========================================
echo.
echo  Seleziona la cartella del tuo progetto.
echo  Poi crea file .cpy e programma in C Python.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\apri_progetto.ps1" -CPythonHome "%CPYTHON_HOME%"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo Operazione annullata o errore.
    pause
    exit /b %ERR%
)

endlocal
exit /b 0

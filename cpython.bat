@echo off
REM Launcher interprete C Python (.cpy / .cp)
setlocal
set "CPYTHON_HOME=%~dp0"
set "CPYTHON_HOME=%CPYTHON_HOME:~0,-1%"
set "PYTHONPATH=%CPYTHON_HOME%;%PYTHONPATH%"

if "%~1"=="" (
    python -m cpython -v
    echo.
    echo Uso: cpython.bat percorso\file.cpy
    echo      cpython.bat --jit percorso\file.cpy
    exit /b 0
)

python -m cpython %*
set "ERR=%ERRORLEVEL%"
endlocal & exit /b %ERR%

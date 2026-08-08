@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "CPYTHON_HOME=%ROOT%"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
set "ARGS="
:cpy_args
if "%~1"=="" goto cpy_run
set ARGS=!ARGS! "%~1"
shift
goto cpy_args
:cpy_run
python -m cpy !ARGS!
set "ERR=!ERRORLEVEL!"
endlocal & exit /b %ERR%

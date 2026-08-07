@echo off
setlocal
cd /d "%~dp0\.."
echo [CPython] Installo dipendenze build...
python -m pip install -r requirements-daemon.txt -q
echo [CPython] Build Cpython_interpreter_64x_win.exe ...
python -m PyInstaller --noconfirm --clean "installer\Cpython_interpreter_64x_win.spec"
if errorlevel 1 (
  echo Build fallita.
  exit /b 1
)
if exist "dist\Cpython_interpreter_64x_win.exe" (
  echo.
  echo OK: dist\Cpython_interpreter_64x_win.exe
  echo Esegui l'EXE una volta per installare (tray + .cpy + cpy run).
) else (
  echo EXE non trovato in dist\
  exit /b 1
)
endlocal

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
  copy /Y "dist\Cpython_interpreter_64x_win.exe" "dist\CPython_Setup.exe" >nul
  echo OK: dist\CPython_Setup.exe
  echo Doppio click su CPython_Setup.exe per installare.
) else (
  echo EXE non trovato in dist\
  exit /b 1
)
endlocal

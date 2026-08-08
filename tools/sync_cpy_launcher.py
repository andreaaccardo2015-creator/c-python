"""Aggiorna cpy.bat in LOCALAPPDATA e sincronizza pacchetti cpy/cpython."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from daemon.paths import install_root  # noqa: E402


def main() -> int:
    dest_root = install_root()
    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / "bin").mkdir(exist_ok=True)

    for pkg in ("cpy", "cpython"):
        src = ROOT / pkg
        dst = dest_root / pkg
        if not src.is_dir():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # Preferisci python -m cpy (sorgenti aggiornati). EXE frozen resta fallback.
    bat = dest_root / "bin" / "cpy.bat"
    bat.write_text(
        f"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "CPYTHON_HOME={dest_root}"
set "PYTHONPATH=%CPYTHON_HOME%;%PYTHONPATH%"
set "ARGS="
:cpy_args
if "%~1"=="" goto cpy_run
set ARGS=!ARGS! "%~1"
shift
goto cpy_args
:cpy_run
where python >nul 2>&1
if errorlevel 1 goto try_exe
python -m cpy !ARGS!
set "ERR=!ERRORLEVEL!"
endlocal & exit /b %ERR%
:try_exe
if exist "%CPYTHON_HOME%\\Cpython_interpreter_64x_win.exe" (
  "%CPYTHON_HOME%\\Cpython_interpreter_64x_win.exe" --cli !ARGS!
  set "ERR=!ERRORLEVEL!"
  endlocal & exit /b %ERR%
)
echo cpy: Python non trovato e EXE assente.
endlocal & exit /b 1
""",
        encoding="utf-8",
    )

    # Anche install.py resta allineato per future installazioni
    from daemon.install import _write_cpy_launcher

    # Scrive template "prefer python" anche via install helper override sotto
    print("ok", bat)
    print("cpy synced ->", dest_root / "cpy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

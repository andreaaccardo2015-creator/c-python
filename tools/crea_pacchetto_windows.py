"""Crea pacchetto Windows: zip + Setup.exe (auto-install al doppio click).

Nota: Windows BLOCCA l'esecuzione automatica all'estrazione di uno .zip
(sicurezza). Il massimo possibile e':
  1) CPython_Setup.exe  → un doppio click installa tutto
  2) CPython_Windows.zip → contiene Setup.exe + INSTALLA.bat
  3) (opz.) SFX IExpress → .exe che estrae e lancia l'installazione
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
EXE_NAME = "Cpython_interpreter_64x_win.exe"
SETUP_NAME = "CPython_Setup.exe"
ZIP_NAME = "CPython_Windows.zip"
PACK_DIR = DIST / "CPython_Windows"


LEGGIMI = """C Python — installazione Windows
=================================

IMPORTANTE
----------
Windows non permette a uno ZIP di avviare programmi da solo
(protezione antivirus / sicurezza).

COSA FARE (10 secondi)
----------------------
1. Estrai questo zip in una cartella
2. Fai DOPPIO CLICK su:  CPython_Setup.exe
   (oppure su INSTALLA.bat)

L'installazione:
- mette C Python nel PC
- attiva il demone in background
- aggiunge il comando  cpy  al PATH
- associa i file .cpy / .cp

Poi apri un NUOVO terminale e prova:
  cpy version
  cpy run tuoFile.cpy

Cartella installazione:
  %LOCALAPPDATA%\\CPython
"""


INSTALLA_BAT = r"""@echo off
setlocal
cd /d "%~dp0"
title C Python — installazione
echo.
echo  ========================================
echo   C Python — installazione automatica
echo  ========================================
echo.
if not exist "%~dp0CPython_Setup.exe" if not exist "%~dp0Cpython_interpreter_64x_win.exe" (
  echo ERRORE: EXE non trovato in questa cartella.
  pause
  exit /b 1
)
if exist "%~dp0CPython_Setup.exe" (
  start "" "%~dp0CPython_Setup.exe" --install
) else (
  start "" "%~dp0Cpython_interpreter_64x_win.exe" --install
)
echo.
echo  Si apre la finestra di installazione.
echo  Poi apri un NUOVO terminale e digita:  cpy version
echo.
timeout /t 4 >nul
endlocal
"""


def _find_exe() -> Path:
    for p in (
        DIST / EXE_NAME,
        DIST / SETUP_NAME,
        ROOT / EXE_NAME,
    ):
        if p.is_file():
            return p
    raise SystemExit(
        f"EXE non trovato. Compila prima con:\n"
        f"  installer\\build.bat\n"
        f"Atteso: {DIST / EXE_NAME}"
    )


def _write_pack_files(exe_src: Path) -> Path:
    if PACK_DIR.exists():
        shutil.rmtree(PACK_DIR)
    PACK_DIR.mkdir(parents=True)

    setup = PACK_DIR / SETUP_NAME
    shutil.copy2(exe_src, setup)
    # Copia anche col nome "tecnico" (compat)
    shutil.copy2(exe_src, PACK_DIR / EXE_NAME)

    (PACK_DIR / "LEGGIMI.txt").write_text(LEGGIMI, encoding="utf-8")
    (PACK_DIR / "INSTALLA.bat").write_text(INSTALLA_BAT, encoding="utf-8")

    # VBS: avvio senza finestra nera (comodo dopo extract)
    (PACK_DIR / "INSTALLA_SILENZIOSO.vbs").write_text(
        'Set sh = CreateObject("WScript.Shell")\r\n'
        'sh.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)\r\n'
        'If CreateObject("Scripting.FileSystemObject").FileExists("CPython_Setup.exe") Then\r\n'
        '  sh.Run "CPython_Setup.exe --install", 1, False\r\n'
        "Else\r\n"
        '  sh.Run "Cpython_interpreter_64x_win.exe --install", 1, False\r\n'
        "End If\r\n",
        encoding="ascii",
        newline="\r\n",
    )
    return setup


def _make_zip() -> Path:
    zip_path = DIST / ZIP_NAME
    if zip_path.is_file():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(PACK_DIR.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=f"CPython_Windows/{f.relative_to(PACK_DIR).as_posix()}")
    return zip_path


def _make_iexpress_sfx(exe_src: Path) -> Path | None:
    """Crea CPython_Setup_Auto.exe che estrae e lancia --install (solo Windows + IExpress)."""
    if sys.platform != "win32":
        return None
    iexpress = shutil.which("iexpress")
    if not iexpress:
        # Path tipico
        for cand in (
            Path(r"C:\Windows\System32\iexpress.exe"),
            Path(r"C:\Windows\SysWOW64\iexpress.exe"),
        ):
            if cand.is_file():
                iexpress = str(cand)
                break
    if not iexpress:
        print("IExpress non trovato: salto SFX auto-estrattore")
        return None

    sfx_dir = DIST / "sfx_build"
    if sfx_dir.exists():
        shutil.rmtree(sfx_dir)
    sfx_dir.mkdir(parents=True)
    bundled = sfx_dir / EXE_NAME
    shutil.copy2(exe_src, bundled)

    out_sfx = DIST / "CPython_Setup_Auto.exe"
    if out_sfx.is_file():
        out_sfx.unlink()

    # SED per IExpress (estrai + lancia install)
    sed = sfx_dir / "cpython.sed"
    # Percorsi con spazi: IExpress e' sensibile; usiamo path corti nella cartella dist
    sed.write_text(
        "\n".join(
            [
                "[Version]",
                "Class=IEXPRESS",
                "SEDVersion=3",
                "[Options]",
                "PackagePurpose=InstallApp",
                "ShowInstallProgramWindow=1",
                "HideExtractAnimation=1",
                "UseLongFileName=1",
                "InsideCompressed=0",
                "CAB_FixedSize=0",
                "CAB_ResvCodeSigning=0",
                "RebootMode=N",
                "InstallPrompt=",
                "DisplayLicense=",
                "FinishMessage=",
                f"TargetName={out_sfx}",
                "FriendlyName=C Python Setup",
                f"AppLaunched={EXE_NAME} --install",
                "PostInstallCmd=<None>",
                "AdminQuietInstCmd=",
                "UserQuietInstCmd=",
                "SourceFiles=SourceFiles",
                "[Strings]",
                "FILE0=" + EXE_NAME,
                "[SourceFiles]",
                f"SourceFiles0={sfx_dir}\\",
                "[SourceFiles0]",
                "%FILE0%=",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        r = subprocess.run(
            [iexpress, "/N", str(sed)],
            cwd=str(sfx_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if out_sfx.is_file() and out_sfx.stat().st_size > 1000:
            print("ok SFX", out_sfx, out_sfx.stat().st_size)
            return out_sfx
        print("IExpress fallito:", r.returncode, (r.stdout or "")[:200], (r.stderr or "")[:200])
    except Exception as e:
        print("IExpress errore:", e)
    return None


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    exe = _find_exe()
    print("exe", exe)

    setup = _write_pack_files(exe)
    # Setup anche in dist/ root (download diretto senza zip)
    shutil.copy2(exe, DIST / SETUP_NAME)
    print("ok", setup)

    zip_path = _make_zip()
    print("ok", zip_path, zip_path.stat().st_size)

    sfx = _make_iexpress_sfx(exe)
    if sfx:
        # Metti anche lo SFX nello zip pack per chi vuole un solo click dopo extract? 
        # No: lo SFX e' il download preferito al posto dello zip.
        pass

    print()
    print("Pronto:")
    print(f"  - {DIST / SETUP_NAME}     (consigliato: doppio click = installa)")
    print(f"  - {zip_path}              (extract + doppio click Setup/INSTALLA)")
    if sfx:
        print(f"  - {sfx}   (auto-estrattore: estrae e installa)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

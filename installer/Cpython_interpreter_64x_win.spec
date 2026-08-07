# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec → Cpython_interpreter_64x_win.exe"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
if not (ROOT / "installer" / "entry.py").is_file():
    ROOT = Path(SPECPATH).resolve()  # se lo spec e' nella root

datas = [
    (str(ROOT / "logo.ico"), "."),
    (str(ROOT / "logo.png"), "."),
    (str(ROOT / "cpython"), "cpython"),
    (str(ROOT / "daemon"), "daemon"),
    (str(ROOT / "cpy"), "cpy"),
    (str(ROOT / "library"), "library"),
    (str(ROOT / "editors"), "editors"),
    (str(ROOT / "tools"), "tools"),
]

dll = ROOT / "llvm_backend" / "build" / "cpython_llvm.dll"
if dll.is_file():
    datas.append((str(dll), "llvm_backend/build"))

a = Analysis(
    [str(ROOT / "installer" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "daemon",
        "daemon.__main__",
        "daemon.tray",
        "daemon.server",
        "daemon.install",
        "daemon.associate",
        "daemon.associate_win",
        "daemon.associate_common",
        "daemon.watcher",
        "daemon.paths",
        "cpy",
        "cpy.__main__",
        "cpython",
        "cpython.interpreter",
        "cpython.lexer",
        "cpython.parser",
        "cpython.values",
        "cpython.environment",
        "pystray",
        "PIL",
        "PIL.Image",
        "pygame",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Cpython_interpreter_64x_win",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "logo.ico") if (ROOT / "logo.ico").is_file() else None,
)

# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec → Cpython_interpreter_64x_win.exe"""

import re
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
if not (ROOT / "installer" / "entry.py").is_file():
    ROOT = Path(SPECPATH).resolve()  # se lo spec e' nella root

VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "cpython" / "__init__.py").read_text(encoding="utf-8"),
).group(1)
_parts = ([int(n) for n in VERSION.split(".")] + [0, 0, 0, 0])[:4]

# I metadati di versione rendono l'eseguibile identificabile: senza di essi
# l'euristica degli antivirus tratta un binario PyInstaller come sospetto.
VERSION_FILE = ROOT / "installer" / "_version_info.txt"
VERSION_FILE.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple(_parts)},
    prodvers={tuple(_parts)},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Andrea Accardo'),
        StringStruct('FileDescription', 'C Python - installer e runtime del linguaggio C Python'),
        StringStruct('FileVersion', '{VERSION}'),
        StringStruct('InternalName', 'Cpython_interpreter'),
        StringStruct('LegalCopyright', 'Copyright (c) 2026 Andrea Accardo - Licenza MIT'),
        StringStruct('OriginalFilename', 'CPython_Setup.exe'),
        StringStruct('ProductName', 'C Python'),
        StringStruct('ProductVersion', '{VERSION}'),
        StringStruct('Comments', 'Sorgenti completi: https://github.com/andreaaccardo2015-creator/c-python'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
    encoding="utf-8",
)

datas = [
    (str(ROOT / "logo.ico"), "."),
    (str(ROOT / "logo.png"), "."),
    (str(ROOT / "LICENSE"), "."),
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
    # UPX resta disattivato: la compressione del binario e' la firma euristica
    # piu' segnalata dagli antivirus, perche' usata dai malware per offuscarsi.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(VERSION_FILE),
    icon=str(ROOT / "logo.ico") if (ROOT / "logo.ico").is_file() else None,
)

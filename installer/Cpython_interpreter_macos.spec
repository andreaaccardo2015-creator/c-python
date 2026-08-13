# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec macOS → Cpython_interpreter.app"""

import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
if not (ROOT / "installer" / "entry.py").is_file():
    ROOT = Path(SPECPATH).resolve()

VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "cpython" / "__init__.py").read_text(encoding="utf-8"),
).group(1)

datas = [
    (str(ROOT / "logo.png"), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "cpython"), "cpython"),
    (str(ROOT / "daemon"), "daemon"),
    (str(ROOT / "cpy"), "cpy"),
    (str(ROOT / "library"), "library"),
    (str(ROOT / "editors"), "editors"),
    (str(ROOT / "tools"), "tools"),
]
if (ROOT / "logo.icns").is_file():
    datas.append((str(ROOT / "logo.icns"), "."))
if (ROOT / "logo.ico").is_file():
    datas.append((str(ROOT / "logo.ico"), "."))

for libname in ("libcpython_llvm.dylib", "cpython_llvm.dylib"):
    dll = ROOT / "llvm_backend" / "build" / libname
    if dll.is_file():
        datas.append((str(dll), "llvm_backend/build"))

icon = str(ROOT / "logo.icns") if (ROOT / "logo.icns").is_file() else None

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
        "daemon.associate_mac",
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
        "cpython.ipc",
        "cpython.cli",
        "cpython.ast_nodes",
        "cpython.errors",
        "pystray",
        "PIL",
        "PIL.Image",
        "pygame",
        "AppKit",
        "Foundation",
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
    name="Cpython_interpreter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # Vedi la spec Windows: la compressione UPX fa scattare l'euristica antivirus.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # utile su macOS per aprire file
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

app = BUNDLE(
    exe,
    name="Cpython_interpreter.app",
    icon=icon,
    bundle_identifier="com.cpython.interpreter",
    info_plist={
        "CFBundleName": "C Python",
        "CFBundleDisplayName": "C Python Interpreter",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHumanReadableCopyright": "Copyright (c) 2026 Andrea Accardo - Licenza MIT",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "C Python Source",
                "CFBundleTypeRole": "Editor",
                "CFBundleTypeExtensions": ["cpy", "cp"],
                "LSItemContentTypes": ["com.cpython.source"],
                "CFBundleTypeIconFile": "logo",
            }
        ],
        "UTExportedTypeDeclarations": [
            {
                "UTTypeIdentifier": "com.cpython.source",
                "UTTypeDescription": "C Python Source File",
                "UTTypeConformsTo": ["public.source-code", "public.plain-text"],
                "UTTypeTagSpecification": {
                    "public.filename-extension": ["cpy", "cp"],
                    "public.mime-type": "text/x-cpython",
                },
            }
        ],
        "CFBundleURLTypes": [],
        "NSAppleEventsUsageDescription": "C Python usa eventi di sistema per il demone in background.",
    },
)

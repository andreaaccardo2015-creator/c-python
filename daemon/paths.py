"""Percorsi installazione e risorse (Windows / macOS / Linux)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def install_root() -> Path:
    """Directory di installazione utente."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
        return base / "CPython"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "CPython"
    # Linux
    xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(xdg) / "CPython"


def bundle_root() -> Path:
    """Root risorse (dev = repo, frozen = _MEIPASS o Contents/Resources)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        exe = Path(sys.executable).resolve()
        # .app: .../Cpython_interpreter.app/Contents/MacOS/exe
        if sys.platform == "darwin" and "Contents/MacOS" in str(exe):
            resources = exe.parent.parent / "Resources"
            if resources.is_dir():
                return resources
        return exe.parent
    return Path(__file__).resolve().parent.parent


def app_executable() -> Path:
    """Percorso dell'eseguibile installato / bundle."""
    root = install_root()
    if sys.platform == "darwin":
        for p in (
            Path.home() / "Applications" / "Cpython_interpreter.app" / "Contents" / "MacOS" / "Cpython_interpreter",
            Path("/Applications/Cpython_interpreter.app/Contents/MacOS/Cpython_interpreter"),
            root / "Cpython_interpreter.app" / "Contents" / "MacOS" / "Cpython_interpreter",
            root / "Cpython_interpreter",
        ):
            if p.is_file():
                return p
    else:
        for name in ("Cpython_interpreter_64x_win.exe", "Cpython_interpreter.exe"):
            p = root / name
            if p.is_file():
                return p
    if is_frozen():
        return Path(sys.executable).resolve()
    return Path(sys.executable)


def logo_ico() -> Path:
    for p in (
        install_root() / "logo.ico",
        bundle_root() / "logo.ico",
        Path(sys.executable).resolve().parent / "logo.ico",
    ):
        if p.is_file():
            return p
    return bundle_root() / "logo.ico"


def logo_png() -> Path:
    for p in (
        install_root() / "logo.png",
        bundle_root() / "logo.png",
        bundle_root() / "logo.icns",
    ):
        if p.is_file() and p.suffix.lower() == ".png":
            return p
    for p in (install_root() / "logo.png", bundle_root() / "logo.png"):
        if p.is_file():
            return p
    return bundle_root() / "logo.png"


def logo_icns() -> Path:
    for p in (
        install_root() / "logo.icns",
        bundle_root() / "logo.icns",
    ):
        if p.is_file():
            return p
    return bundle_root() / "logo.icns"


def pid_file() -> Path:
    return install_root() / "daemon.pid"


def ensure_install_dirs() -> Path:
    root = install_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "bin").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    return root

"""Associazione macOS: LaunchAgent, UTI/.cpy, editor, PATH hint."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import install_root, logo_icns, logo_png


LAUNCH_AGENT_ID = "com.cpython.interpreter"
LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_ID}.plist"


def register_file_association(open_command: str | None = None) -> None:
    """
    Su macOS l'associazione primaria e' nell'Info.plist del .app
    (CFBundleDocumentTypes). Qui:
    - aggiorniamo editor (VS Code / Cursor)
    - opzionale duti se installato
    - assicuriamo icone/logo in Application Support
    """
    root = install_root()
    root.mkdir(parents=True, exist_ok=True)

    # Copia icone
    for src_fn, name in ((logo_png, "logo.png"), (logo_icns, "logo.icns")):
        try:
            p = src_fn()
            if p.is_file():
                shutil.copy2(p, root / name)
        except Exception:
            pass

    from .associate_common import patch_editor_associations

    patch_editor_associations()

    # Se duti e' disponibile, associa .cpy/.cp al bundle
    _try_duti()

    # Hint lsregister se l'app e' in Applications
    _refresh_launch_services()


def _app_bundle_candidates() -> list[Path]:
    from .paths import MAC_APP_BUNDLE, install_root

    names = (MAC_APP_BUNDLE, "Cpython_interpreter.app")
    out: list[Path] = []
    for name in names:
        out.extend(
            [
                Path("/Applications") / name,
                Path.home() / "Applications" / name,
                install_root() / name,
            ]
        )
    return out


def _try_duti() -> None:
    duti = shutil.which("duti")
    if not duti:
        return
    bid = "com.cpython.interpreter"
    for ext in ("cpy", "cp"):
        try:
            subprocess.run([duti, "-s", bid, ext, "all"], check=False, capture_output=True)
        except Exception:
            pass


def _refresh_launch_services() -> None:
    for app in _app_bundle_candidates():
        if not app.is_dir():
            continue
        try:
            subprocess.run(
                ["/System/Library/Frameworks/CoreServices.framework/Frameworks/"
                 "LaunchServices.framework/Support/lsregister", "-f", str(app)],
                check=False,
                capture_output=True,
            )
        except Exception:
            # percorso alternativo
            try:
                subprocess.run(["lsregister", "-f", str(app)], check=False, capture_output=True)
            except Exception:
                pass


def register_startup(exe_path: Path) -> None:
    """LaunchAgent: demone al login."""
    LAUNCH_AGENT.parent.mkdir(parents=True, exist_ok=True)

    # Se e' dentro un .app, usa l'eseguibile MacOS
    program = str(exe_path.resolve())
    # Per .app bundle, exe_path puo' essere il binario interno
    plist = {
        "Label": LAUNCH_AGENT_ID,
        "ProgramArguments": [program, "--daemon"],
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
        "StandardOutPath": str(install_root() / "logs" / "daemon.out.log"),
        "StandardErrorPath": str(install_root() / "logs" / "daemon.err.log"),
    }
    install_root().joinpath("logs").mkdir(parents=True, exist_ok=True)
    with LAUNCH_AGENT.open("wb") as f:
        plistlib.dump(plist, f)

    # Carica agent (best-effort)
    try:
        subprocess.run(["launchctl", "unload", str(LAUNCH_AGENT)], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", str(LAUNCH_AGENT)], check=False, capture_output=True)
    except Exception:
        pass


def unregister_startup() -> None:
    try:
        if LAUNCH_AGENT.is_file():
            subprocess.run(["launchctl", "unload", str(LAUNCH_AGENT)], check=False, capture_output=True)
            LAUNCH_AGENT.unlink(missing_ok=True)
    except Exception:
        pass


def notify_shell_change() -> None:
    _refresh_launch_services()

"""Monitor background: ogni 2 secondi controlla file .cpy e tiene vivo il servizio."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from .associate import notify_shell_change, register_file_association
from .paths import ensure_install_dirs, install_root, logo_ico


POLL_S = 2.0
MAX_DEPTH = 4
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "AppData",
    ".cache",
    "dist",
    "build",
    ".cursor",
}


def _default_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "OneDrive",
        home / "source",
        home / "projects",
        home / "Progetti",
        install_root(),
    ]
    # Cartella recente Windows
    recent = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Recent"
    if recent.is_dir():
        roots.append(recent)
    # Repo / home install se noti
    for env in ("CPYTHON_HOME", "CURSOR_PROJECT"):
        v = os.environ.get(env)
        if v:
            roots.append(Path(v))
    # Workspace Cursor aperti di recente (path tipici)
    cursor = home / ".cursor" / "projects"
    if cursor.is_dir():
        roots.append(cursor)
    return [r for r in roots if r]


def _iter_cpy(root: Path, max_depth: int = MAX_DEPTH):
    """Trova .cpy/.cp senza esplodere tutto il disco."""
    if not root.is_dir():
        return
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        name = entry.name
                        if entry.is_dir(follow_symlinks=False):
                            if depth < max_depth and name not in SKIP_DIRS and not name.startswith("."):
                                stack.append((Path(entry.path), depth + 1))
                        elif entry.is_file(follow_symlinks=False):
                            low = name.lower()
                            if low.endswith(".cpy") or low.endswith(".cp"):
                                yield Path(entry.path)
                    except OSError:
                        continue
        except OSError:
            continue


def _signal(path: Path, event: str) -> None:
    root = ensure_install_dirs()
    payload = {
        "event": event,
        "path": str(path.resolve()),
        "language": "cpython",
        "icon": str(logo_ico()),
        "ts": time.time(),
    }
    marker = root / "last_cpy_signal.json"
    try:
        marker.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    # Log rotativo leggero
    try:
        log = root / "logs" / "monitor.log"
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{payload['ts']:.0f} {event} {payload['path']}\n")
    except OSError:
        pass


def _write_heartbeat(extra: dict | None = None) -> None:
    root = ensure_install_dirs()
    data = {
        "alive": True,
        "ts": time.time(),
        "poll_s": POLL_S,
        "pid": os.getpid(),
    }
    if extra:
        data.update(extra)
    try:
        (root / "heartbeat.json").write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def start_background_monitor(poll_s: float = POLL_S) -> threading.Thread:
    """
    Loop invisibile ogni 2s:
    - nuovi / modificati .cpy → segnale linguaggio + logo
    - ri-conferma associazione .cpy
    - heartbeat (prova che l'EXE e' vivo)
    """
    roots = _default_roots()
    # path -> mtime
    known: dict[str, float] = {}
    for root in roots:
        for p in _iter_cpy(root):
            try:
                known[str(p.resolve())] = p.stat().st_mtime
            except OSError:
                pass

    stop = threading.Event()
    ticks = 0

    def loop() -> None:
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            found = 0
            created = 0
            changed = 0
            try:
                for root in roots:
                    for p in _iter_cpy(root):
                        found += 1
                        try:
                            key = str(p.resolve())
                            mtime = p.stat().st_mtime
                        except OSError:
                            continue
                        prev = known.get(key)
                        if prev is None:
                            known[key] = mtime
                            created += 1
                            _signal(p, "created")
                        elif mtime > prev + 0.01:
                            known[key] = mtime
                            changed += 1
                            _signal(p, "modified")
                # Associazione .cpy ogni ~30s (non ogni tick: winreg e' lento)
                if ticks % 15 == 1:
                    try:
                        register_file_association()
                    except Exception:
                        pass
                if ticks % 30 == 0:
                    try:
                        notify_shell_change()
                    except Exception:
                        pass
            except Exception:
                pass

            _write_heartbeat(
                {
                    "files_tracked": len(known),
                    "last_scan_found": found,
                    "created": created,
                    "changed": changed,
                    "tick": ticks,
                }
            )
            stop.wait(poll_s)

    t = threading.Thread(target=loop, name="cpython-monitor", daemon=True)
    t.start()
    return t


# Alias compatibile
def watch_for_cpy(roots: list[Path] | None = None, poll_s: float = POLL_S) -> threading.Thread:
    return start_background_monitor(poll_s=poll_s)

"""System tray + avvio demone (sempre in background, senza finestra)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

from . import APP_NAME, DEFAULT_HOST, DEFAULT_PORT
from .paths import logo_ico, logo_png, pid_file, ensure_install_dirs
from .server import serve


def _write_pid() -> None:
    ensure_install_dirs()
    pid_file().write_text(str(os.getpid()), encoding="utf-8")


def _clear_pid() -> None:
    try:
        pid_file().unlink(missing_ok=True)
    except Exception:
        pass


def _hide_console() -> None:
    """Niente finestra nera: processo invisibile."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def run_daemon(show_tray: bool = False) -> None:
    """
    Demone sempre attivo.
    Di default invisibile (no console, no popup).
    show_tray=True lascia solo l'icona nella tray di sistema.
    """
    _hide_console()
    ensure_install_dirs()
    _write_pid()
    httpd = serve()

    def serve_forever():
        httpd.serve_forever()

    t = threading.Thread(target=serve_forever, name="cpython-http", daemon=True)
    t.start()

    if show_tray and sys.platform == "win32":
        try:
            _run_tray(httpd)
            return
        except Exception:
            pass

    # Background puro: resta vivo finché vive il server
    try:
        t.join()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        _clear_pid()


def _run_tray(httpd) -> None:
    import pystray
    from PIL import Image

    png = logo_png()
    ico = logo_ico()
    if png.is_file():
        image = Image.open(png).convert("RGBA")
    elif ico.is_file():
        image = Image.open(ico).convert("RGBA")
    else:
        image = Image.new("RGBA", (64, 64), (47, 95, 173, 255))

    def on_quit(icon, _item):
        icon.stop()
        httpd.shutdown()
        _clear_pid()

    def on_status(icon, _item):
        import urllib.request

        try:
            with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/health", timeout=2) as r:
                msg = r.read().decode("utf-8")
        except Exception as e:
            msg = f"offline: {e}"
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 0x40)
        except Exception:
            print(msg)

    menu = pystray.Menu(
        pystray.MenuItem(f"{APP_NAME} (background)", None, enabled=False),
        pystray.MenuItem("Stato servizio", on_status),
        pystray.MenuItem("Esci", on_quit),
    )
    icon = pystray.Icon("cpython", image, APP_NAME, menu)
    icon.run()


def is_daemon_alive() -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def _creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    # Nessuna finestra, processo staccato
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS  # type: ignore
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


def start_daemon_detached(exe: Path | None = None) -> None:
    """Avvia il demone in background (invisibile)."""
    if is_daemon_alive():
        return
    common = dict(
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        common["creationflags"] = _creation_flags()
    else:
        common["start_new_session"] = True

    if exe and exe.is_file():
        subprocess.Popen([str(exe), "--daemon"], **common)
        return
    root = Path(__file__).resolve().parent.parent
    env = {**os.environ, "PYTHONPATH": str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    subprocess.Popen(
        [sys.executable, "-m", "daemon", "--daemon"],
        cwd=str(root),
        env=env,
        **common,
    )

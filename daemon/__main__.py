"""Entry point demone / installer / CLI."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Forward CLI: Cpython_interpreter_64x_win.exe --cli run file.cpy
    if "--cli" in argv:
        i = argv.index("--cli")
        from cpy.__main__ import main as cpy_main

        return cpy_main(argv[i + 1 :])

    # Apri file .cpy (associazione Windows)
    if "--open" in argv:
        i = argv.index("--open")
        path = argv[i + 1] if i + 1 < len(argv) else ""
        if path:
            import subprocess

            for cmd in (["code", path], ["notepad.exe", path]):
                try:
                    subprocess.Popen(cmd)
                    break
                except Exception:
                    continue
            try:
                import json
                import urllib.request

                data = json.dumps({"path": path, "event": "open"}).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:39271/notify-cpy",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=2)
            except Exception:
                pass
        return 0

    parser = argparse.ArgumentParser(prog="CPython", description="C Python Interpreter service")
    parser.add_argument("--daemon", action="store_true", help="Avvia demone in background (invisibile)")
    parser.add_argument("--tray", action="store_true", help="Mostra icona nella tray di sistema")
    parser.add_argument("--install", action="store_true", help="Installa su questo PC")
    parser.add_argument("--uninstall", action="store_true", help="Disinstalla servizio")
    parser.add_argument(
        "--from-dmg-install",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if args.install:
        from .install import do_install

        return do_install()

    if args.uninstall:
        from .install import do_uninstall

        return do_uninstall()

    # Default EXE: se parte dal .dmg, prima si sposta in Applicazioni.
    if not args.daemon and getattr(sys, "frozen", False):
        from .install import is_installed, do_install, maybe_install_from_dmg
        from .tray import is_daemon_alive, run_daemon
        from .watcher import start_background_monitor
        from .associate import register_file_association, notify_shell_change

        relocated = maybe_install_from_dmg(argv)
        if relocated is not None:
            return relocated

        if not is_installed():
            rc = do_install()
            if rc != 0:
                return rc
        if is_daemon_alive():
            return 0  # gia' attivo: esci in silenzio
        try:
            register_file_association()
            notify_shell_change()
        except Exception:
            pass
        start_background_monitor(poll_s=2.0)
        run_daemon(show_tray=args.tray)
        return 0

    if args.daemon:
        from .tray import run_daemon
        from .watcher import start_background_monitor
        from .associate import register_file_association, notify_shell_change

        try:
            register_file_association()
            notify_shell_change()
        except Exception:
            pass
        # Controlla ogni 2 secondi: nuovi .cpy, modifiche, associazione, heartbeat
        start_background_monitor(poll_s=2.0)
        run_daemon(show_tray=args.tray)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

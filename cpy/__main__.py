"""CLI pubblica: cpy run file.cpy"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT = "http://127.0.0.1:39271"


def _post(path: str, payload: dict, timeout: float = 120.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{DEFAULT}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _notify_daemon(path: Path, event: str = "run") -> None:
    try:
        urllib.request.urlopen(f"{DEFAULT}/health", timeout=0.5)
    except Exception:
        try:
            from daemon.tray import start_daemon_detached

            start_daemon_detached(None)
        except Exception:
            return
    try:
        _post("/notify-cpy", {"path": str(path), "event": event}, timeout=2.0)
    except Exception:
        pass


def _run_local(path: Path, jit: bool) -> int:
    """Esegue nel terminale corrente (stdin/stdout reali → getinput funziona)."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from cpython.errors import CPythonError
    from cpython.interpreter import Interpreter

    source = path.read_text(encoding="utf-8")
    interp = Interpreter(filename=str(path), enable_jit=jit)
    try:
        interp.run_source(source)
        return 0
    except CPythonError as e:
        print(f"Errore: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrotto.", file=sys.stderr)
        return 130
    except EOFError:
        print(
            "\nErrore: input terminato (EOF). "
            "Usa `cpy run` in un terminale interattivo per getinput.",
            file=sys.stderr,
        )
        return 1


def cmd_run(file: str, jit: bool, via_daemon: bool = False) -> int:
    path = Path(file).resolve()
    if not path.is_file():
        print(f"File non trovato: {path}", file=sys.stderr)
        return 1
    if path.suffix.lower() not in (".cpy", ".cp"):
        print("Avviso: estensione consigliata .cpy", file=sys.stderr)

    _notify_daemon(path, "run")

    # Di default: esecuzione locale (getinput / print funzionano nel terminale)
    if not via_daemon:
        return _run_local(path, jit)

    # Modalita' batch: demone HTTP (niente input interattivo)
    try:
        result = _post("/run", {"path": str(path), "jit": jit})
    except urllib.error.URLError as e:
        print(f"Impossibile contattare il demone: {e}", file=sys.stderr)
        return 2

    sys.stdout.write(result.get("stdout") or "")
    sys.stderr.write(result.get("stderr") or "")
    return int(result.get("exit_code") or 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cpy",
        description="C Python — esegue file .cpy (getinput nel terminale)",
    )
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Esegue un file .cpy")
    run_p.add_argument("file", help="Percorso file .cpy")
    run_p.add_argument("--no-jit", action="store_true")
    run_p.add_argument(
        "--daemon",
        action="store_true",
        help="Esegue via demone HTTP (batch, senza input interattivo)",
    )

    sub.add_parser("status", help="Stato demone")
    sub.add_parser("version", help="Versione")

    args = parser.parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args.file, jit=not args.no_jit, via_daemon=args.daemon)
    if args.cmd == "status":
        try:
            with urllib.request.urlopen(f"{DEFAULT}/health", timeout=2) as r:
                print(r.read().decode("utf-8"))
            return 0
        except Exception as e:
            print(f"offline: {e}")
            return 1
    if args.cmd == "version":
        print("cpy 0.2.1 (C Python client)")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

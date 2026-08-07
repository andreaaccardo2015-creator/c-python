"""Server HTTP locale: esegue file .cpy e risponde all'CLI cpy."""

from __future__ import annotations

import io
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import DEFAULT_HOST, DEFAULT_PORT


def run_cpy_file(path: Path, enable_jit: bool = True) -> dict[str, Any]:
    """Esegue un file .cpy catturando stdout/stderr."""
    # Assicura che il package cpython sia importabile
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from cpython.errors import CPythonError
    from cpython.interpreter import Interpreter

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    code = 0
    try:
        sys.stdout = stdout_buf
        sys.stderr = stderr_buf
        if not path.is_file():
            print(f"File non trovato: {path}", file=sys.stderr)
            code = 1
        else:
            source = path.read_text(encoding="utf-8")
            interp = Interpreter(filename=str(path.resolve()), enable_jit=enable_jit)
            try:
                interp.run_source(source)
            except CPythonError as e:
                print(f"Errore: {e}", file=sys.stderr)
                code = 1
            except EOFError:
                print(
                    "Errore: getinput richiede un terminale interattivo.\n"
                    "Usa: cpy run tuoFile.cpy  (senza --daemon)",
                    file=sys.stderr,
                )
                code = 1
            except SystemExit as e:
                code = int(e.code) if isinstance(e.code, int) else 1
            except Exception:
                traceback.print_exc(file=sys.stderr)
                code = 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err

    return {
        "ok": code == 0,
        "exit_code": code,
        "stdout": stdout_buf.getvalue(),
        "stderr": stderr_buf.getvalue(),
        "path": str(path),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # silenzioso
        return

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            self._json(200, {"ok": True, "service": "CPython", "version": "0.2.0"})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "json non valido"})
            return

        if path == "/run":
            file_path = body.get("path") or body.get("file")
            if not file_path:
                self._json(400, {"ok": False, "error": "manca path"})
                return
            enable_jit = bool(body.get("jit", True))
            result = run_cpy_file(Path(file_path), enable_jit=enable_jit)
            self._json(200, result)
            return

        if path == "/notify-cpy":
            # Segnale: file .cpy creato/aperto — gli editor con estensione C Python
            # ascoltano via file marker / health; qui registriamo solo l'evento.
            marker = Path(__file__).resolve().parent.parent
            try:
                from .paths import install_root

                marker = install_root() / "last_cpy_signal.json"
            except Exception:
                marker = Path.home() / "last_cpy_signal.json"
            try:
                marker.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            self._json(200, {"ok": True, "signaled": True, "path": body.get("path")})
            return

        self._json(404, {"ok": False, "error": "not found"})


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    return httpd

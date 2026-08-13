"""Demone C Python — sempre attivo: esecuzione, tray, associazione .cpy."""

from __future__ import annotations

try:
    from cpython import __version__
except Exception:  # pacchetto cpython non importabile (build parziale)
    __version__ = "0.3.4"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39271
APP_NAME = "C Python Interpreter"

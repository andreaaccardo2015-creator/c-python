"""Libreria time — pause e orologi."""

from __future__ import annotations

import time as _time
from typing import Any


def breakcode(seconds: Any) -> None:
    """Pausa il programma per N secondi (come time.sleep)."""
    _time.sleep(float(seconds))


def sleep(seconds: Any) -> None:
    breakcode(seconds)


def now() -> float:
    """Timestamp Unix corrente in secondi."""
    return _time.time()


def clock() -> float:
    """Tempo monotono (utile per misurare durata)."""
    return _time.perf_counter()


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "time",
        {
            "breakcode": NativeFunction("breakcode", breakcode),
            "sleep": NativeFunction("sleep", sleep),
            "now": NativeFunction("now", now),
            "clock": NativeFunction("clock", clock),
        },
    )

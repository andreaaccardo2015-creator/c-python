"""Libreria random — numeri e scelte casuali."""

from __future__ import annotations

import random as _random
from typing import Any


def seed(value: Any = None) -> None:
    """Imposta il seed del generatore casuale."""
    if value is None:
        _random.seed()
    else:
        _random.seed(value)


def int_(a: Any, b: Any | None = None) -> int:
    """
    random.int(max) -> 0..max inclusivo
    random.int(min, max) -> min..max inclusivo
    """
    if b is None:
        return _random.randint(0, int(a))
    return _random.randint(int(a), int(b))


def float_(a: Any = 0.0, b: Any = 1.0) -> float:
    """random.float(min, max) — float in [min, max)."""
    return _random.uniform(float(a), float(b))


def choice(items: Any) -> Any:
    """Sceglie un elemento a caso da una lista."""
    return _random.choice(list(items))


def shuffle(items: Any) -> list:
    """Restituisce una nuova lista mescolata."""
    data = list(items)
    _random.shuffle(data)
    return data


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "random",
        {
            "seed": NativeFunction("seed", seed),
            "int": NativeFunction("int", int_),
            "float": NativeFunction("float", float_),
            "choice": NativeFunction("choice", choice),
            "shuffle": NativeFunction("shuffle", shuffle),
        },
    )

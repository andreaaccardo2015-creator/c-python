"""Libreria math — funzioni matematiche."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _stdlib_math():
    """Importa il math di Python evitando la shadow library/math."""
    lib = str(Path(__file__).resolve().parent.parent)
    removed = False
    if lib in sys.path:
        sys.path.remove(lib)
        removed = True
    cached = sys.modules.pop("math", None)
    try:
        import math as m

        return m
    finally:
        if removed:
            sys.path.insert(0, lib)
        # non rimettere cached se era la nostra lib incompleta
        if cached is not None and getattr(cached, "__file__", None) == __file__:
            pass
        elif cached is not None and "math" not in sys.modules:
            sys.modules["math"] = cached


_math = _stdlib_math()


def abs_(x: Any) -> float:
    return abs(float(x))


def min_(*args: Any) -> float:
    return float(min(float(a) for a in args))


def max_(*args: Any) -> float:
    return float(max(float(a) for a in args))


def clamp(x: Any, lo: Any, hi: Any) -> float:
    v = float(x)
    return max(float(lo), min(float(hi), v))


def floor(x: Any) -> int:
    return int(_math.floor(float(x)))


def ceil(x: Any) -> int:
    return int(_math.ceil(float(x)))


def round_(x: Any, digits: Any = 0) -> float:
    return round(float(x), int(digits))


def sqrt(x: Any) -> float:
    return _math.sqrt(float(x))


def pow_(x: Any, y: Any) -> float:
    return float(x) ** float(y)


def sin(x: Any) -> float:
    return _math.sin(float(x))


def cos(x: Any) -> float:
    return _math.cos(float(x))


def tan(x: Any) -> float:
    return _math.tan(float(x))


def atan2(y: Any, x: Any) -> float:
    return _math.atan2(float(y), float(x))


def deg(rad: Any) -> float:
    return _math.degrees(float(rad))


def rad(deg_v: Any) -> float:
    return _math.radians(float(deg_v))


def lerp(a: Any, b: Any, t: Any) -> float:
    aa, bb, tt = float(a), float(b), float(t)
    return aa + (bb - aa) * tt


def dist(x1: Any, y1: Any, x2: Any, y2: Any) -> float:
    return _math.hypot(float(x2) - float(x1), float(y2) - float(y1))


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "math",
        {
            "pi": _math.pi,
            "e": _math.e,
            "abs": NativeFunction("abs", abs_),
            "min": NativeFunction("min", min_),
            "max": NativeFunction("max", max_),
            "clamp": NativeFunction("clamp", clamp),
            "floor": NativeFunction("floor", floor),
            "ceil": NativeFunction("ceil", ceil),
            "round": NativeFunction("round", round_),
            "sqrt": NativeFunction("sqrt", sqrt),
            "pow": NativeFunction("pow", pow_),
            "sin": NativeFunction("sin", sin),
            "cos": NativeFunction("cos", cos),
            "tan": NativeFunction("tan", tan),
            "atan2": NativeFunction("atan2", atan2),
            "deg": NativeFunction("deg", deg),
            "rad": NativeFunction("rad", rad),
            "lerp": NativeFunction("lerp", lerp),
            "dist": NativeFunction("dist", dist),
        },
    )

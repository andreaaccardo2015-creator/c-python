"""Libreria json — encode/decode JSON."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _stdlib_json():
    lib = str(Path(__file__).resolve().parent.parent)
    removed = False
    if lib in sys.path:
        sys.path.remove(lib)
        removed = True
    cached = sys.modules.pop("json", None)
    try:
        import json as j

        return j
    finally:
        if removed:
            sys.path.insert(0, lib)
        if cached is not None and getattr(cached, "__file__", None) == __file__:
            pass
        elif cached is not None and "json" not in sys.modules:
            sys.modules["json"] = cached


_json = _stdlib_json()


def encode(value: Any) -> str:
    return _json.dumps(value, ensure_ascii=False)


def decode(text: Any) -> Any:
    return _json.loads(str(text))


def load(path: Any) -> Any:
    return _json.loads(Path(str(path)).read_text(encoding="utf-8"))


def save(path: Any, value: Any) -> None:
    Path(str(path)).write_text(
        _json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "json",
        {
            "encode": NativeFunction("encode", encode),
            "decode": NativeFunction("decode", decode),
            "load": NativeFunction("load", load),
            "save": NativeFunction("save", save),
        },
    )

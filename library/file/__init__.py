"""Libreria file — lettura e scrittura file di testo."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read(path: Any) -> str:
    return Path(str(path)).read_text(encoding="utf-8")


def write(path: Any, content: Any) -> None:
    Path(str(path)).write_text(str(content), encoding="utf-8")


def append(path: Any, content: Any) -> None:
    p = Path(str(path))
    with p.open("a", encoding="utf-8") as f:
        f.write(str(content))


def exists(path: Any) -> bool:
    return Path(str(path)).exists()


def delete(path: Any) -> None:
    p = Path(str(path))
    if p.is_file():
        p.unlink()


def lines(path: Any) -> list:
    text = read(path)
    return text.splitlines()


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "file",
        {
            "read": NativeFunction("read", read),
            "write": NativeFunction("write", write),
            "append": NativeFunction("append", append),
            "exists": NativeFunction("exists", exists),
            "delete": NativeFunction("delete", delete),
            "lines": NativeFunction("lines", lines),
        },
    )

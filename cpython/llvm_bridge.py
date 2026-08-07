"""Bridge ctypes verso libcpython_llvm (ORC JIT o stub C++)."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Optional


def _candidate_dlls() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    names = [
        "cpython_llvm.dll",
        "libcpython_llvm.dll",
        "libcpython_llvm.so",
        "libcpython_llvm.dylib",
        "cpython_llvm.so",
    ]
    dirs = [
        root / "llvm_backend" / "build",
        root / "llvm_backend" / "build" / "Release",
        root / "llvm_backend" / "build" / "Debug",
        root / "build",
    ]
    out: list[Path] = []
    for d in dirs:
        for n in names:
            out.append(d / n)
    env = os.environ.get("CPYTHON_LLVM_DLL")
    if env:
        out.insert(0, Path(env))
    return out


class JitEngine:
    def __init__(self, lib: ctypes.CDLL):
        self._lib = lib
        self._lib.cp_jit_create.restype = ctypes.c_void_p
        self._lib.cp_jit_destroy.argtypes = [ctypes.c_void_p]
        self._lib.cp_jit_compile_func.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        self._lib.cp_jit_compile_func.restype = ctypes.c_int
        self._lib.cp_jit_call_i64.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_longlong),
            ctypes.c_int,
        ]
        self._lib.cp_jit_call_i64.restype = ctypes.c_longlong
        self._lib.cp_jit_call_f64.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]
        self._lib.cp_jit_call_f64.restype = ctypes.c_double
        self._lib.cp_jit_is_llvm.restype = ctypes.c_int
        self._eng = self._lib.cp_jit_create()
        if not self._eng:
            raise RuntimeError("cp_jit_create failed")

    @property
    def is_llvm(self) -> bool:
        return bool(self._lib.cp_jit_is_llvm())

    def compile(self, name: str, ir_text: str) -> None:
        err = ctypes.create_string_buffer(512)
        rc = self._lib.cp_jit_compile_func(
            self._eng,
            name.encode("utf-8"),
            ir_text.encode("utf-8"),
            err,
            512,
        )
        if rc != 0:
            raise RuntimeError(err.value.decode("utf-8", errors="replace") or f"compile rc={rc}")

    def call_i64(self, name: str, args: list[int]) -> int:
        n = len(args)
        arr = (ctypes.c_longlong * n)(*[int(a) for a in args]) if n else (ctypes.c_longlong * 0)()
        return int(self._lib.cp_jit_call_i64(self._eng, name.encode("utf-8"), arr, n))

    def call_f64(self, name: str, args: list[float]) -> float:
        n = len(args)
        arr = (ctypes.c_double * n)(*[float(a) for a in args]) if n else (ctypes.c_double * 0)()
        return float(self._lib.cp_jit_call_f64(self._eng, name.encode("utf-8"), arr, n))

    def close(self) -> None:
        if self._eng:
            self._lib.cp_jit_destroy(self._eng)
            self._eng = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


_engine: Optional[JitEngine] = None
_load_attempted = False
_load_error: Optional[str] = None


def jit_available() -> bool:
    return get_engine() is not None


def jit_load_error() -> Optional[str]:
    get_engine()
    return _load_error


def get_engine() -> Optional[JitEngine]:
    global _engine, _load_attempted, _load_error
    if _engine is not None:
        return _engine
    if _load_attempted:
        return None
    _load_attempted = True
    for path in _candidate_dlls():
        if not path.is_file():
            continue
        try:
            # Aggiungi dir DLL al path di ricerca Windows
            if sys.platform == "win32":
                os.add_dll_directory(str(path.parent))
            lib = ctypes.CDLL(str(path))
            _engine = JitEngine(lib)
            _load_error = None
            return _engine
        except OSError as e:
            _load_error = f"{path}: {e}"
            continue
        except Exception as e:
            _load_error = str(e)
            continue
    if _load_error is None:
        _load_error = "DLL cpython_llvm non trovata (compila llvm_backend/)"
    return None

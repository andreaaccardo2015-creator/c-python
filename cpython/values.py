from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from . import ast_nodes as ast
from .environment import Environment, FloatHint, InputSpec, coerce_to_type
from .errors import RuntimeError_


def _ci_get_attr(obj: Any, name: str) -> Any:
    """getattr case-insensitive (per linguaggio C Python)."""
    if hasattr(obj, name):
        return getattr(obj, name)
    lname = name.lower()
    # match esatto ignorando case su attributi pubblici
    for attr in dir(obj):
        if attr.lower() == lname:
            return getattr(obj, attr)
    raise AttributeError(name)


def _ci_has_attr(obj: Any, name: str) -> bool:
    if hasattr(obj, name):
        return True
    lname = name.lower()
    return any(attr.lower() == lname for attr in dir(obj))


def _ci_dict_get(d: dict, name: str, default: Any = None) -> Any:
    if name in d:
        return d[name]
    lname = name.lower()
    for k, v in d.items():
        if isinstance(k, str) and k.lower() == lname:
            return v
    return default


def _ci_dict_has(d: dict, name: str) -> bool:
    if name in d:
        return True
    lname = name.lower()
    return any(isinstance(k, str) and k.lower() == lname for k in d)



class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


@dataclass
class Function:
    name: str
    params: list[tuple[str, str]]
    body: list[ast.Node]
    closure: Environment
    return_type: Optional[str] = None
    is_method: bool = False
    jit_ready: bool = False
    jit_failed: bool = False

    def arity(self) -> int:
        return len(self.params)


@dataclass
class ClassInfo:
    name: str
    base: Optional["ClassInfo"]
    methods: dict[str, Function] = field(default_factory=dict)
    fields: dict[str, tuple[str, Any]] = field(default_factory=dict)  # name -> (type, default)
    native: Any = None  # optional Python class/factory for finityengine bridge


@dataclass
class Instance:
    class_info: ClassInfo
    fields: dict[str, Any] = field(default_factory=dict)
    native: Any = None  # linked Python object (Behaviour, etc.)

    def get(self, name: str) -> Any:
        key = name.lower()
        if _ci_dict_has(self.fields, key):
            return _ci_dict_get(self.fields, key)
        # look up method
        method = _ci_dict_get(self.class_info.methods, key)
        if method is None and self.class_info.base:
            method = self._find_method(key, self.class_info.base)
        if method is not None:
            return BoundMethod(method, self)
        # native attribute
        if self.native is not None and _ci_has_attr(self.native, key):
            return _ci_get_attr(self.native, key)
        # field defaults from class hierarchy
        default = self._find_field(key, self.class_info)
        if default is not None:
            return default
        raise RuntimeError_(f"Attributo '{name}' non trovato su {self.class_info.name}")

    def _find_method(self, name: str, cls: ClassInfo) -> Optional[Function]:
        method = _ci_dict_get(cls.methods, name)
        if method is not None:
            return method
        if cls.base:
            return self._find_method(name, cls.base)
        return None

    def _find_field(self, name: str, cls: ClassInfo) -> Any:
        if _ci_dict_has(self.fields, name):
            return _ci_dict_get(self.fields, name)
        if _ci_dict_has(cls.fields, name):
            return _ci_dict_get(cls.fields, name)[1]
        if cls.base:
            return self._find_field(name, cls.base)
        return None

    def set(self, name: str, value: Any) -> None:
        key = name.lower()
        if self.native is not None and _ci_has_attr(self.native, key) and not _ci_dict_has(self.fields, key):
            # Prefer setting on native for engine props like transform
            try:
                # trova nome reale sull'oggetto
                real = key
                for attr in dir(self.native):
                    if attr.lower() == key:
                        real = attr
                        break
                setattr(self.native, real, value)
                return
            except Exception:
                pass
        self.fields[key] = value


@dataclass
class BoundMethod:
    function: Function
    instance: Instance


@dataclass
class Module:
    name: str
    env: Environment
    exports: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        key = name.lower()
        if _ci_dict_has(self.exports, key):
            return _ci_dict_get(self.exports, key)
        return self.env.get(key)


class NativeFunction:
    def __init__(self, name: str, fn: Callable[..., Any], arity: int | None = None):
        self.name = name
        self.fn = fn
        self._arity = arity

    def __call__(self, *args: Any) -> Any:
        return self.fn(*args)


class NativeModule:
    """Oggetto modulo con attributi Python esposti a C Python."""

    def __init__(self, name: str, attrs: dict[str, Any]):
        self.name = name
        # chiavi normalizzate: GetKey / getkey / GETKEY → stesso attributo
        self.attrs = {str(k).lower(): v for k, v in attrs.items()}

    def get(self, name: str) -> Any:
        key = str(name).lower()
        if key not in self.attrs:
            raise RuntimeError_(f"Modulo '{self.name}' non ha '{name}'")
        return self.attrs[key]

    def __getattr__(self, name: str) -> Any:
        # for Python-side access
        try:
            return self.get(name)
        except RuntimeError_ as e:
            raise AttributeError(str(e)) from e

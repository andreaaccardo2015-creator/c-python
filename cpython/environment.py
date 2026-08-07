from __future__ import annotations

from typing import Any, Optional

from .errors import RuntimeError_


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: dict[str, Any] = {}
        self.types: dict[str, str] = {}

    @staticmethod
    def _key(name: str) -> str:
        return name.lower() if isinstance(name, str) else name

    def define(self, name: str, value: Any, type_name: str | None = None) -> None:
        key = self._key(name)
        self.values[key] = value
        if type_name:
            self.types[key] = type_name.lower() if isinstance(type_name, str) else type_name

    def assign(self, name: str, value: Any) -> None:
        key = self._key(name)
        if key in self.values:
            expected = self.types.get(key)
            if expected:
                value = coerce_to_type(value, expected)
            self.values[key] = value
            return
        if self.parent:
            self.parent.assign(key, value)
            return
        raise RuntimeError_(f"Variabile non definita: '{name}'")

    def get(self, name: str) -> Any:
        key = self._key(name)
        if key in self.values:
            return self.values[key]
        if self.parent:
            return self.parent.get(key)
        raise RuntimeError_(f"Variabile non definita: '{name}'")

    def has(self, name: str) -> bool:
        key = self._key(name)
        if key in self.values:
            return True
        if self.parent:
            return self.parent.has(key)
        return False


def coerce_to_type(value: Any, type_name: str) -> Any:
    if type_name == "any" or type_name is None:
        return value
    if type_name == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            return int(float(value)) if "." in value else int(value)
        raise RuntimeError_(f"Impossibile convertire {value!r} in int")
    if type_name == "float":
        if isinstance(value, (int, float, bool)):
            return float(value)
        if isinstance(value, str):
            return float(value)
        if isinstance(value, FloatHint):
            raise RuntimeError_("Valore float non valido")
        if isinstance(value, InputSpec):
            return value  # resolved later by getinput path
        raise RuntimeError_(f"Impossibile convertire {value!r} in float")
    if type_name == "string":
        if isinstance(value, InputSpec):
            return value
        return str(value) if value is not None else ""
    if type_name == "bool":
        return bool(value)
    if type_name == "list":
        if isinstance(value, list):
            return value
        raise RuntimeError_(f"Attesa list, ricevuto {type(value).__name__}")
    if type_name == "dict":
        if isinstance(value, dict):
            return value
        raise RuntimeError_(f"Atteso dict, ricevuto {type(value).__name__}")
    return value


class FloatHint:
    """Sentinel `f` usato in getinput(... + f) per chiedere un float."""

    def __repr__(self) -> str:
        return "f"

    def __add__(self, other):
        if isinstance(other, str):
            return InputSpec(other, "float")
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return InputSpec(other, "float")
        return NotImplemented


class InputSpec:
    def __init__(self, prompt: str, kind: str = "string"):
        self.prompt = prompt
        self.kind = kind

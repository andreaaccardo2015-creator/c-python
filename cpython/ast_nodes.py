from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Node:
    line: int = 0
    column: int = 0


@dataclass
class Program(Node):
    body: list[Node] = field(default_factory=list)


@dataclass
class Import(Node):
    name: str = ""


@dataclass
class VarDecl(Node):
    type_name: str = ""
    name: str = ""
    value: Optional[Node] = None


@dataclass
class Assign(Node):
    target: Node = None  # type: ignore
    value: Node = None  # type: ignore


@dataclass
class If(Node):
    condition: Node = None  # type: ignore
    then_body: list[Node] = field(default_factory=list)
    else_body: list[Node] = field(default_factory=list)


@dataclass
class While(Node):
    condition: Node = None  # type: ignore
    body: list[Node] = field(default_factory=list)


@dataclass
class For(Node):
    var: str = ""
    iterable: Node = None  # type: ignore
    body: list[Node] = field(default_factory=list)


@dataclass
class FunDef(Node):
    name: str = ""
    params: list[tuple[str, str]] = field(default_factory=list)  # (type, name)
    return_type: Optional[str] = None
    body: list[Node] = field(default_factory=list)


@dataclass
class ClassDef(Node):
    name: str = ""
    base: Optional[Node] = None  # Attribute or Name
    members: list[Node] = field(default_factory=list)


@dataclass
class Return(Node):
    value: Optional[Node] = None
    type_name: Optional[str] = None  # return int expr


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class ExprStmt(Node):
    expr: Node = None  # type: ignore


@dataclass
class BinaryOp(Node):
    op: str = ""
    left: Node = None  # type: ignore
    right: Node = None  # type: ignore


@dataclass
class UnaryOp(Node):
    op: str = ""
    operand: Node = None  # type: ignore


@dataclass
class Call(Node):
    callee: Node = None  # type: ignore
    args: list[Node] = field(default_factory=list)


@dataclass
class Attribute(Node):
    object: Node = None  # type: ignore
    attr: str = ""


@dataclass
class Index(Node):
    object: Node = None  # type: ignore
    index: Node = None  # type: ignore


@dataclass
class Name(Node):
    id: str = ""


@dataclass
class Literal(Node):
    value: Any = None


@dataclass
class ListLiteral(Node):
    elements: list[Node] = field(default_factory=list)


@dataclass
class DictLiteral(Node):
    pairs: list[tuple[Node, Node]] = field(default_factory=list)


@dataclass
class NewInstance(Node):
    """class_name(...) — costruttore."""
    callee: Node = None  # type: ignore
    args: list[Node] = field(default_factory=list)


@dataclass
class ActorDecl(Node):
    """actor player — dichiara un Actor e collega lo script."""
    name: str = ""


@dataclass
class PositionLiteral(Node):
    """x 0; y 0"""
    x: Node = None  # type: ignore
    y: Node = None  # type: ignore

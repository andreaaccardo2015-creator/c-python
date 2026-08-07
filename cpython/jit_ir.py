"""Serializzazione AST → IR testuale per il backend C++/LLVM e check purezza."""

from __future__ import annotations

from . import ast_nodes as ast

_ALLOWED_PARAM = {"int", "float", "bool"}
_BIN = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "%": "mod",
    "==": "eq",
    "!=": "ne",
    "<": "lt",
    "<=": "le",
    ">": "gt",
    ">=": "ge",
    "and": "and",
    "or": "or",
}


def map_ty(type_name: str | None) -> str | None:
    if type_name == "int":
        return "i64"
    if type_name == "float":
        return "f64"
    if type_name == "bool":
        return "bool"
    return None


def is_jittable_function(node: ast.FunDef) -> bool:
    ret = node.return_type or _infer_from_returns(node.body)
    if not ret or map_ty(ret) is None:
        return False
    for t, _name in node.params:
        if t not in _ALLOWED_PARAM:
            return False
    return _body_ok(node.body)


def _infer_from_returns(body: list[ast.Node]) -> str | None:
    for stmt in body:
        t = _ret_type_in(stmt)
        if t:
            return t
    return None


def _ret_type_in(node: ast.Node) -> str | None:
    if isinstance(node, ast.Return) and node.type_name:
        return node.type_name
    if isinstance(node, ast.If):
        for s in node.then_body + node.else_body:
            t = _ret_type_in(s)
            if t:
                return t
    if isinstance(node, ast.While):
        for s in node.body:
            t = _ret_type_in(s)
            if t:
                return t
    return None


def _body_ok(body: list[ast.Node]) -> bool:
    for stmt in body:
        if not _stmt_ok(stmt):
            return False
    return True


def _stmt_ok(node: ast.Node) -> bool:
    if isinstance(node, ast.Return):
        return node.value is None or _expr_ok(node.value)
    if isinstance(node, (ast.Break, ast.Continue)):
        return True
    if isinstance(node, ast.VarDecl):
        if node.type_name not in _ALLOWED_PARAM:
            return False
        return node.value is None or _expr_ok(node.value)
    if isinstance(node, ast.Assign):
        if not isinstance(node.target, ast.Name):
            return False
        return _expr_ok(node.value)
    if isinstance(node, ast.If):
        return _expr_ok(node.condition) and _body_ok(node.then_body) and _body_ok(node.else_body)
    if isinstance(node, ast.While):
        return _expr_ok(node.condition) and _body_ok(node.body)
    if isinstance(node, ast.ExprStmt):
        return _expr_ok(node.expr)
    return False


def _expr_ok(node: ast.Node) -> bool:
    if isinstance(node, ast.Literal):
        return isinstance(node.value, (int, float, bool)) or node.value is None
    if isinstance(node, ast.Name):
        return node.id != "this"
    if isinstance(node, ast.UnaryOp):
        return node.op in ("-", "+", "not") and _expr_ok(node.operand)
    if isinstance(node, ast.BinaryOp):
        return node.op in _BIN and _expr_ok(node.left) and _expr_ok(node.right)
    return False


class _Emitter:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.temp = 0
        self.label = 0

    def fresh(self) -> str:
        self.temp += 1
        return f"t{self.temp}"

    def fresh_label(self, prefix: str = "L") -> str:
        self.label += 1
        return f"{prefix}{self.label}"

    def emit_expr(self, node: ast.Node) -> str:
        if isinstance(node, ast.Literal):
            dest = self.fresh()
            if isinstance(node.value, bool):
                self.lines.append(f"{dest} = {'true' if node.value else 'false'}")
            elif isinstance(node.value, float):
                self.lines.append(f"{dest} = {node.value}")
            elif isinstance(node.value, int):
                self.lines.append(f"{dest} = {node.value}")
            else:
                self.lines.append(f"{dest} = 0")
            return dest
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.UnaryOp):
            a = self.emit_expr(node.operand)
            dest = self.fresh()
            if node.op == "-":
                self.lines.append(f"{dest} = neg {a}")
            elif node.op == "not":
                self.lines.append(f"{dest} = not {a}")
            else:
                self.lines.append(f"{dest} = {a}")
            return dest
        if isinstance(node, ast.BinaryOp):
            op = _BIN[node.op]
            # short-circuit and/or via jumps would be nicer; stub does eager eval
            a = self.emit_expr(node.left)
            b = self.emit_expr(node.right)
            dest = self.fresh()
            self.lines.append(f"{dest} = {op} {a} {b}")
            return dest
        raise ValueError(f"espressione non JIT: {type(node).__name__}")

    def emit_stmt(self, node: ast.Node, break_label: str | None = None, cont_label: str | None = None) -> None:
        if isinstance(node, ast.Return):
            if node.value is None:
                self.lines.append("ret 0")
            else:
                v = self.emit_expr(node.value)
                self.lines.append(f"ret {v}")
            return
        if isinstance(node, ast.Break):
            if not break_label:
                raise ValueError("break fuori da ciclo")
            self.lines.append(f"jmp {break_label}")
            return
        if isinstance(node, ast.Continue):
            if not cont_label:
                raise ValueError("continue fuori da ciclo")
            self.lines.append(f"jmp {cont_label}")
            return
        if isinstance(node, ast.VarDecl):
            if node.value is not None:
                v = self.emit_expr(node.value)
                self.lines.append(f"{node.name} = {v}")
            else:
                self.lines.append(f"{node.name} = 0")
            return
        if isinstance(node, ast.Assign):
            assert isinstance(node.target, ast.Name)
            v = self.emit_expr(node.value)
            self.lines.append(f"{node.target.id} = {v}")
            return
        if isinstance(node, ast.ExprStmt):
            self.emit_expr(node.expr)
            return
        if isinstance(node, ast.If):
            else_l = self.fresh_label("else")
            end_l = self.fresh_label("endif")
            cond = self.emit_expr(node.condition)
            if node.else_body:
                self.lines.append(f"jz {cond} {else_l}")
                for s in node.then_body:
                    self.emit_stmt(s, break_label, cont_label)
                self.lines.append(f"jmp {end_l}")
                self.lines.append(f"{else_l}:")
                for s in node.else_body:
                    self.emit_stmt(s, break_label, cont_label)
                self.lines.append(f"{end_l}:")
            else:
                self.lines.append(f"jz {cond} {end_l}")
                for s in node.then_body:
                    self.emit_stmt(s, break_label, cont_label)
                self.lines.append(f"{end_l}:")
            return
        if isinstance(node, ast.While):
            head = self.fresh_label("while")
            end = self.fresh_label("endwhile")
            self.lines.append(f"{head}:")
            cond = self.emit_expr(node.condition)
            self.lines.append(f"jz {cond} {end}")
            for s in node.body:
                self.emit_stmt(s, break_label=end, cont_label=head)
            self.lines.append(f"jmp {head}")
            self.lines.append(f"{end}:")
            return
        raise ValueError(f"statement non JIT: {type(node).__name__}")


def emit_function_ir(node: ast.FunDef) -> str:
    """Produce IR testuale per cp_jit_compile_func."""
    ret_name = node.return_type or _infer_from_returns(node.body)
    ret = map_ty(ret_name)
    assert ret is not None
    lines = [f"fun {node.name}", f"rettype {ret}"]
    for t, name in node.params:
        lines.append(f"param {name} {map_ty(t)}")
    lines.append("block")
    em = _Emitter()
    for stmt in node.body:
        em.emit_stmt(stmt)
    # se non c'è return esplicito sull'ultimo path, aggiungi ret 0
    if not any(isinstance(s, ast.Return) for s in node.body):
        em.lines.append("ret 0")
    lines.extend(em.lines)
    lines.append("end")
    return "\n".join(lines) + "\n"

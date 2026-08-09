from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from . import ast_nodes as ast
from .environment import Environment, FloatHint, InputSpec, coerce_to_type
from .errors import RuntimeError_
from .parser import Parser
from .values import (
    BoundMethod,
    BreakSignal,
    ClassInfo,
    ContinueSignal,
    Function,
    Instance,
    Module,
    NativeFunction,
    NativeModule,
    ReturnSignal,
)


class Interpreter:
    def __init__(self, filename: str | None = None, enable_jit: bool | None = None):
        self.globals = Environment()
        self.env = self.globals
        self.filename = filename
        self.current_actor: Any = None
        self.module_cache: dict[str, Any] = {}
        self.search_paths: list[Path] = []
        # None = auto (usa JIT se DLL presente), True forza, False disabilita
        self.enable_jit = True if enable_jit is None else enable_jit
        self._jit_warned = False
        if filename:
            self.search_paths.append(Path(filename).resolve().parent)
        # package roots (dev / install utente / PyInstaller)
        import sys

        root = self._package_root()
        self.search_paths.append(root)
        self.search_paths.append(root / "library")
        self.search_paths.append(root / "cpython" / "stdlib")
        # Python import path for native packages (finityengine, ...)
        lib = str(root / "library")
        if lib not in sys.path:
            sys.path.insert(0, lib)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self._install_builtins()

    @staticmethod
    def _package_root() -> Path:
        """Root con cpython/ + library/ (funziona anche da EXE frozen)."""
        import sys

        candidates: list[Path] = []
        env = os.environ.get("CPYTHON_HOME")
        if env:
            candidates.append(Path(env))
        here = Path(__file__).resolve().parent.parent
        candidates.append(here)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS))  # type: ignore[attr-defined]
            candidates.append(Path(sys.executable).resolve().parent)
        try:
            from daemon.paths import bundle_root, install_root

            candidates.append(install_root())
            candidates.append(bundle_root())
        except Exception:
            pass
        for root in candidates:
            if (root / "library").is_dir() and (root / "cpython").is_dir():
                return root
        for root in candidates:
            if (root / "library").is_dir() or (root / "cpython").is_dir():
                return root
        return here

    def _install_builtins(self) -> None:
        print_mod = NativeModule(
            "print",
            {
                "log": NativeFunction("log", self._builtin_print),
                "output": NativeFunction("output", self._builtin_print_output),
            },
        )
        self.globals.define("print", print_mod)
        self.globals.define("getinput", NativeFunction("getinput", self._builtin_getinput))
        self.globals.define(
            "getcollision", NativeFunction("getcollision", self._builtin_getcollision)
        )
        self.globals.define("range", NativeFunction("range", self._builtin_range))
        self.globals.define("len", NativeFunction("len", lambda x: len(x)))
        self.globals.define("str", NativeFunction("str", lambda x: str(x)))
        self.globals.define("int", NativeFunction("int", lambda x: int(x)))
        self.globals.define("float", NativeFunction("float", lambda x: float(x)))
        self.globals.define("bool", NativeFunction("bool", lambda x: bool(x)))
        self.globals.define("f", FloatHint())  # float hint for getinput(... + f)
        self.globals.define("fullscreen", "fullscreen")  # per screen.create(fullscreen, "...")

    def _builtin_print(self, *args: Any) -> None:
        print(*(self._stringify(a) for a in args))

    def _builtin_print_output(self, *args: Any) -> None:
        # print.output("text" value) — juxtaposition becomes separate args if comma,
        # but in example: print.output("la tua operazione fa:" numero1 + numero2)
        # that's two args if space-separated? In our grammar, space doesn't separate args —
        # need comma OR it's one expression. Looking at example:
        # print.output("la tua operazione fa:" numero1 + numero2)
        # This is INVALID in our parser (two expressions). We'll support implicit string join
        # by treating it as: first string + " " + rest if user uses comma:
        # Official: print.output("la tua operazione fa:", numero1 + numero2)
        parts = [self._stringify(a) for a in args]
        print(" ".join(parts))

    def _builtin_getcollision(self, name: Any = None) -> bool:
        """if (getcollision "muro") — l'actor dello script corrente tocca 'name'?"""
        try:
            import finityengine

            return bool(finityengine.get_collision(name))
        except Exception:
            return False

    def _builtin_getinput(self, prompt: Any = "") -> Any:
        kind = "string"
        text = ""
        if isinstance(prompt, InputSpec):
            text = prompt.prompt
            kind = prompt.kind
        elif isinstance(prompt, FloatHint):
            text = ""
            kind = "float"
        else:
            text = self._stringify(prompt)
        raw = input(text)
        if kind == "float":
            return float(raw)
        return raw

    def _builtin_range(self, *args: Any) -> list:
        return list(range(*args))

    def _stringify(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, FloatHint):
            return "f"
        return str(value)

    # ---- public API ----
    def run_source(self, source: str) -> None:
        program = Parser.parse_source(source)
        self.exec_program(program)

    def exec_program(self, program: ast.Program) -> None:
        for stmt in program.body:
            self.exec(stmt)

    def exec(self, node: ast.Node) -> Any:
        method = getattr(self, f"exec_{type(node).__name__}", None)
        if method is None:
            raise RuntimeError_(f"Nodo non supportato: {type(node).__name__}", node.line, node.column)
        try:
            return method(node)
        except RuntimeError_ as e:
            if e.line is None:
                e.line = node.line
                e.column = node.column
            raise

    # ---- statements ----
    def exec_Import(self, node: ast.Import) -> None:
        mod = self._load_module(node.name)
        # bind top-level name (first segment)
        top = node.name.split(".")[0]
        self.env.define(top, mod)

    def exec_VarDecl(self, node: ast.VarDecl) -> None:
        value = None
        if node.value is not None:
            value = self.eval(node.value)
            # auto-resolve InputSpec when type is float/int
            if isinstance(value, InputSpec):
                raw = input(value.prompt)
                if node.type_name == "float" or value.kind == "float":
                    value = float(raw)
                elif node.type_name == "int":
                    value = int(float(raw))
                else:
                    value = raw
            else:
                value = coerce_to_type(value, node.type_name)
        else:
            defaults = {"int": 0, "float": 0.0, "string": "", "bool": False, "list": [], "dict": {}}
            value = defaults.get(node.type_name)
        self.env.define(node.name, value, node.type_name)

    def exec_Assign(self, node: ast.Assign) -> None:
        value = self.eval(node.value)
        self._assign_target(node.target, value)

    def _assign_target(self, target: ast.Node, value: Any) -> None:
        if isinstance(target, ast.Name):
            if self.env.has(target.id):
                self.env.assign(target.id, value)
            else:
                self.env.define(target.id, value)
            return
        if isinstance(target, ast.Attribute):
            obj = self.eval(target.object)
            # position = x ..; y ..  → aggiorna Position esistente se presente
            if target.attr == "position" and hasattr(obj, "position"):
                from finityengine import Position

                if isinstance(value, Position):
                    pos = getattr(obj, "position")
                    if isinstance(pos, Position):
                        pos.x = value.x
                        pos.y = value.y
                        return
            if isinstance(obj, Instance):
                obj.set(target.attr, value)
                return
            if isinstance(obj, Module):
                obj.env.assign(target.attr, value)
                return
            if isinstance(obj, NativeModule):
                obj.attrs[target.attr] = value
                return
            # plain Python object
            setattr(obj, target.attr, value)
            return
        if isinstance(target, ast.Index):
            obj = self.eval(target.object)
            idx = self.eval(target.index)
            obj[idx] = value
            return
        raise RuntimeError_("Target di assegnazione non valido", target.line, target.column)

    def exec_ExprStmt(self, node: ast.ExprStmt) -> None:
        self.eval(node.expr)

    def exec_If(self, node: ast.If) -> None:
        if self._truthy(self.eval(node.condition)):
            self._exec_block(node.then_body)
        else:
            self._exec_block(node.else_body)

    def exec_While(self, node: ast.While) -> None:
        while self._truthy(self.eval(node.condition)):
            try:
                self._exec_block(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_For(self, node: ast.For) -> None:
        iterable = self.eval(node.iterable)
        local = Environment(self.env)
        prev = self.env
        self.env = local
        try:
            for item in iterable:
                local.define(node.var, item)
                try:
                    self._exec_block(node.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        finally:
            self.env = prev

    def exec_ActorDecl(self, node: ast.ActorDecl) -> None:
        from finityengine import create_actor

        create_actor(node.name, self)

    def exec_FunDef(self, node: ast.FunDef) -> None:
        fn = Function(
            name=node.name,
            params=node.params,
            body=node.body,
            closure=self.env,
            return_type=node.return_type,
        )
        # Lifecycle legati all'actor corrente (script allocato sull'Actor)
        if node.name in ("OnStart", "OnUpdate", "OnFixedUpdate", "OnCollision") and self.current_actor is not None:
            self.current_actor.bind_handler(node.name, fn, self)
            return
        if self.enable_jit:
            self._try_jit_compile(fn, node)
        self.env.define(node.name, fn)

    def _try_jit_compile(self, fn: Function, node: ast.FunDef) -> None:
        from .jit_ir import emit_function_ir, is_jittable_function
        from .llvm_bridge import get_engine, jit_load_error

        if not is_jittable_function(node):
            return
        eng = get_engine()
        if eng is None:
            if not self._jit_warned:
                import sys

                msg = jit_load_error() or "DLL assente"
                print(f"[cpython] JIT non disponibile ({msg}) — uso interprete", file=sys.stderr)
                self._jit_warned = True
            return
        try:
            ir = emit_function_ir(node)
            eng.compile(fn.name, ir)
            fn.jit_ready = True
        except Exception:
            fn.jit_failed = True

    def exec_ClassDef(self, node: ast.ClassDef) -> None:
        base_info = None
        native_base = None
        if node.base is not None:
            base_val = self.eval(node.base)
            if isinstance(base_val, ClassInfo):
                base_info = base_val
                native_base = base_val.native
            elif isinstance(base_val, type):
                # Python class (e.g. finityengine.Behaviour)
                native_base = base_val
                base_info = ClassInfo(name=base_val.__name__, base=None, native=base_val)
            else:
                raise RuntimeError_(f"Classe base non valida: {base_val!r}", node.line, node.column)

        class_info = ClassInfo(name=node.name, base=base_info, native=native_base)

        # Execute members in a temp env to collect fields/methods
        class_env = Environment(self.env)
        prev = self.env
        self.env = class_env
        try:
            for member in node.members:
                if isinstance(member, ast.VarDecl):
                    default = None
                    if member.value is not None:
                        default = self.eval(member.value)
                    else:
                        defaults = {"int": 0, "float": 0.0, "string": "", "bool": False, "list": [], "dict": {}}
                        default = defaults.get(member.type_name)
                    class_info.fields[member.name] = (member.type_name, default)
                elif isinstance(member, ast.FunDef):
                    fn = Function(
                        name=member.name,
                        params=member.params,
                        body=member.body,
                        closure=self.env,
                        return_type=member.return_type,
                        is_method=True,
                    )
                    class_info.methods[member.name] = fn
                else:
                    self.exec(member)
        finally:
            self.env = prev

        # callable constructor
        def construct(*args: Any) -> Instance:
            return self._instantiate(class_info, args)

        class_info_box = class_info

        # Store ClassInfo; calling it is handled in eval_Call
        self.env.define(node.name, class_info)

    def _instantiate(self, class_info: ClassInfo, args: tuple) -> Instance:
        # collect field defaults from hierarchy
        fields: dict[str, Any] = {}

        def collect(ci: ClassInfo):
            if ci.base:
                collect(ci.base)
            for name, (_t, default) in ci.fields.items():
                fields[name] = default

        collect(class_info)

        native_obj = None
        if class_info.native is not None and isinstance(class_info.native, type):
            try:
                native_obj = class_info.native()
            except TypeError:
                native_obj = class_info.native

        inst = Instance(class_info=class_info, fields=fields, native=native_obj)

        # link instance to native for engine callbacks
        if native_obj is not None:
            setattr(native_obj, "_cp_instance", inst)
            setattr(native_obj, "_cp_interpreter", self)

        # call init if present
        init = class_info.methods.get("init")
        if init is None and class_info.base:
            init = self._find_method(class_info, "init")
        if init is not None:
            self._call_function(init, list(args), this=inst)
        elif args:
            raise RuntimeError_(f"{class_info.name} non accetta argomenti (manca init)")

        return inst

    def _find_method(self, class_info: ClassInfo, name: str) -> Optional[Function]:
        if name in class_info.methods:
            return class_info.methods[name]
        if class_info.base:
            return self._find_method(class_info.base, name)
        return None

    def exec_Return(self, node: ast.Return) -> None:
        value = self.eval(node.value) if node.value is not None else None
        if node.type_name and value is not None:
            value = coerce_to_type(value, node.type_name)
        raise ReturnSignal(value)

    def exec_Break(self, node: ast.Break) -> None:
        raise BreakSignal()

    def exec_Continue(self, node: ast.Continue) -> None:
        raise ContinueSignal()

    def _exec_block(self, body: list[ast.Node], env: Environment | None = None) -> None:
        prev = self.env
        if env is not None:
            self.env = env
        try:
            for stmt in body:
                self.exec(stmt)
        finally:
            self.env = prev

    # ---- expressions ----
    def eval(self, node: ast.Node) -> Any:
        method = getattr(self, f"eval_{type(node).__name__}", None)
        if method is None:
            raise RuntimeError_(f"Espressione non supportata: {type(node).__name__}", node.line, node.column)
        return method(node)

    def eval_Literal(self, node: ast.Literal) -> Any:
        return node.value

    def eval_PositionLiteral(self, node: ast.PositionLiteral) -> Any:
        from finityengine import Position

        return Position(self.eval(node.x), self.eval(node.y))

    def eval_Name(self, node: ast.Name) -> Any:
        if node.id == "this":
            if self.env.has("this"):
                return self.env.get("this")
            raise RuntimeError_("'this' usato fuori da un metodo", node.line, node.column)
        return self.env.get(node.id)

    def eval_ListLiteral(self, node: ast.ListLiteral) -> list:
        return [self.eval(e) for e in node.elements]

    def eval_DictLiteral(self, node: ast.DictLiteral) -> dict:
        return {self.eval(k): self.eval(v) for k, v in node.pairs}

    def eval_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.eval(node.operand)
        if node.op == "-":
            return -operand
        if node.op == "+":
            return +operand
        if node.op == "not":
            return not self._truthy(operand)
        raise RuntimeError_(f"Operatore unario sconosciuto: {node.op}")

    def eval_BinaryOp(self, node: ast.BinaryOp) -> Any:
        if node.op == "and":
            left = self.eval(node.left)
            return self.eval(node.right) if self._truthy(left) else left
        if node.op == "or":
            left = self.eval(node.left)
            return left if self._truthy(left) else self.eval(node.right)

        left = self.eval(node.left)
        right = self.eval(node.right)
        op = node.op

        # FloatHint / InputSpec concatenation
        if op == "+" and (isinstance(left, FloatHint) or isinstance(right, FloatHint) or isinstance(left, InputSpec) or isinstance(right, InputSpec)):
            if isinstance(left, str) and isinstance(right, FloatHint):
                return InputSpec(left, "float")
            if isinstance(left, FloatHint) and isinstance(right, str):
                return InputSpec(right, "float")
            if isinstance(left, InputSpec) and isinstance(right, str):
                return InputSpec(left.prompt + right, left.kind)
            if isinstance(left, str) and isinstance(right, InputSpec):
                return InputSpec(left + right.prompt, right.kind)

        try:
            if op == "+":
                if isinstance(left, str) or isinstance(right, str):
                    return self._stringify(left) + self._stringify(right)
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right
            if op == "%":
                return left % right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
        except TypeError as e:
            raise RuntimeError_(f"Operazione '{op}' non valida tra {type(left).__name__} e {type(right).__name__}: {e}") from e
        raise RuntimeError_(f"Operatore sconosciuto: {op}")

    def eval_Attribute(self, node: ast.Attribute) -> Any:
        from .values import _ci_get_attr, _ci_has_attr, _ci_dict_get, _ci_dict_has

        obj = self.eval(node.object)
        attr = node.attr
        if isinstance(obj, Instance):
            return obj.get(attr)
        if isinstance(obj, Module):
            return obj.get(attr)
        if isinstance(obj, NativeModule):
            return obj.get(attr)
        if isinstance(obj, ClassInfo):
            # static-ish access to nested? or native
            method = _ci_dict_get(obj.methods, attr)
            if method is not None:
                return method
            if obj.native is not None and _ci_has_attr(obj.native, attr):
                return _ci_get_attr(obj.native, attr)
        if _ci_has_attr(obj, attr):
            return _ci_get_attr(obj, attr)
        # dict-like NativeModule attrs on Python modules
        if isinstance(obj, dict) and _ci_dict_has(obj, attr):
            return _ci_dict_get(obj, attr)
        raise RuntimeError_(f"Attributo '{node.attr}' non trovato", node.line, node.column)

    def eval_Index(self, node: ast.Index) -> Any:
        obj = self.eval(node.object)
        idx = self.eval(node.index)
        return obj[idx]

    def eval_Call(self, node: ast.Call) -> Any:
        callee = self.eval(node.callee)
        args = [self.eval(a) for a in node.args]

        if isinstance(callee, ClassInfo):
            return self._instantiate(callee, tuple(args))

        if isinstance(callee, BoundMethod):
            return self._call_function(callee.function, args, this=callee.instance)

        if isinstance(callee, Function):
            return self._call_function(callee, args)

        if isinstance(callee, NativeFunction):
            return callee(*args)

        if callable(callee):
            return callee(*args)

        raise RuntimeError_(f"Oggetto non chiamabile: {callee!r}", node.line, node.column)

    def _call_function(self, fn: Function, args: list[Any], this: Instance | None = None) -> Any:
        if len(args) != len(fn.params):
            raise RuntimeError_(f"{fn.name} attende {len(fn.params)} argomenti, ne ha ricevuti {len(args)}")

        if self.enable_jit and fn.jit_ready and this is None:
            from .llvm_bridge import get_engine

            eng = get_engine()
            if eng is not None:
                try:
                    return self._call_jit(fn, args, eng)
                except Exception:
                    fn.jit_ready = False
                    fn.jit_failed = True

        local = Environment(fn.closure)
        if this is not None:
            local.define("this", this)
        for (type_name, pname), aval in zip(fn.params, args):
            local.define(pname, coerce_to_type(aval, type_name) if type_name != "any" else aval, type_name)
        prev = self.env
        self.env = local
        try:
            for stmt in fn.body:
                self.exec(stmt)
        except ReturnSignal as ret:
            result = ret.value
            if fn.return_type:
                result = coerce_to_type(result, fn.return_type)
            return result
        finally:
            self.env = prev
        return None

    def _call_jit(self, fn: Function, args: list[Any], eng: Any) -> Any:
        use_float = fn.return_type == "float" or any(t == "float" for t, _ in fn.params)
        if use_float:
            fargs = []
            for (t, _), a in zip(fn.params, args):
                if t == "bool":
                    fargs.append(1.0 if a else 0.0)
                else:
                    fargs.append(float(a))
            result = eng.call_f64(fn.name, fargs)
            if fn.return_type == "int":
                return int(result)
            if fn.return_type == "bool":
                return bool(result)
            return float(result)
        iargs = []
        for (t, _), a in zip(fn.params, args):
            if t == "bool":
                iargs.append(1 if a else 0)
            else:
                iargs.append(int(a))
        result = eng.call_i64(fn.name, iargs)
        if fn.return_type == "bool":
            return bool(result)
        if fn.return_type == "float":
            return float(result)
        return int(result)

    def _truthy(self, value: Any) -> bool:
        return bool(value)

    # ---- modules ----
    _NATIVE_LIBS = (
        "finityengine",
        "screen",
        "time",
        "random",
        "sdgame",
        "math",
        "file",
        "audio",
        "json",
    )

    def _load_module(self, name: str) -> Any:
        if name in self.module_cache:
            return self.module_cache[name]

        # Librerie native in library/<nome>/
        if name in self._NATIVE_LIBS:
            mod = self._load_native_lib(name)
            self.module_cache[name] = mod
            return mod

        # .cp / .cpy file on search path
        for ext in (".cpy", ".cp"):
            rel = name.replace(".", os.sep) + ext
            for base in self.search_paths:
                path = base / rel
                if path.is_file():
                    return self._load_cp_file(name, path)
                init_path = base / name.replace(".", os.sep) / f"__init__{ext}"
                if init_path.is_file():
                    return self._load_cp_file(name, init_path)

        raise RuntimeError_(f"Modulo non trovato: {name}")

    def _load_native_lib(self, name: str) -> NativeModule:
        import importlib
        import importlib.util

        # finityengine tiene un singleton (_engine) usato anche da 'actor ...'
        # e da screen.create via import Python normale: va riusata la stessa
        # istanza, altrimenti esistono due motori con due finestre.
        if name == "finityengine":
            package = importlib.import_module("finityengine")
            return package.create_cp_module(self)

        root = Path(__file__).resolve().parent.parent
        init_file = root / "library" / name / "__init__.py"
        if not init_file.is_file():
            raise RuntimeError_(f"Libreria native non trovata: library/{name}")
        spec = importlib.util.spec_from_file_location(f"cp_lib_{name}", init_file)
        if spec is None or spec.loader is None:
            raise RuntimeError_(f"Impossibile caricare libreria '{name}'")
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        if not hasattr(package, "create_cp_module"):
            raise RuntimeError_(f"Libreria '{name}' non espone create_cp_module")
        return package.create_cp_module(self)

    def _load_cp_file(self, name: str, path: Path) -> Module:
        source = path.read_text(encoding="utf-8")
        module_env = Environment(self.globals)
        mod = Module(name=name, env=module_env)
        self.module_cache[name] = mod

        prev_env = self.env
        prev_file = self.filename
        self.env = module_env
        self.filename = str(path)
        self.search_paths.insert(0, path.parent)
        try:
            program = Parser.parse_source(source)
            self.exec_program(program)
            # export all bindings
            mod.exports = dict(module_env.values)
        finally:
            self.env = prev_env
            self.filename = prev_file
        return mod

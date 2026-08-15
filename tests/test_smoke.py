"""Smoke tests per lexer, parser e interprete C Python."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cpython.interpreter import Interpreter
from cpython.lexer import Lexer, TokenType
from cpython.parser import Parser


class TestLexer(unittest.TestCase):
    def test_indent_dedent(self):
        src = "if (true)\n    x = 1\n"
        tokens = Lexer(src).tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.INDENT, types)
        self.assertIn(TokenType.DEDENT, types)

    def test_comment(self):
        tokens = Lexer("// hello\nx = 1\n").tokenize()
        self.assertTrue(any(t.type == TokenType.IDENT and t.value == "x" for t in tokens))

    def test_suffisso_f_e_un_solo_numero(self):
        """2.5f e 90f sono float interi: la f non resta un token a parte."""
        tokens = [t for t in Lexer("2.5f\n90f\n").tokenize() if t.type == TokenType.FLOAT]
        self.assertEqual([t.value for t in tokens], [2.5, 90.0])
        self.assertFalse(any(t.type == TokenType.IDENT for t in Lexer("2.5f\n").tokenize()))

    def test_f_attaccata_a_un_nome_resta_nome(self):
        """2fps non e' un float: la f si prende solo se il numero finisce li'."""
        tokens = Lexer("2fps\n").tokenize()
        self.assertEqual(tokens[0].type, TokenType.INT)
        self.assertTrue(any(t.type == TokenType.IDENT and t.value == "fps" for t in tokens))


class TestParser(unittest.TestCase):
    def test_var_and_if(self):
        src = 'string n = "si"\nif (n == "si")\n    print.log(n)\n'
        prog = Parser.parse_source(src)
        self.assertEqual(len(prog.body), 2)

    def test_fun_class(self):
        src = """
fun add(int a, int b)
    return int a + b

class P
    int vita = 100
    fun hit(int d)
        this.vita = this.vita - d
"""
        prog = Parser.parse_source(src)
        self.assertEqual(len(prog.body), 2)

    def test_on_start_update_braces(self):
        src = """
class Player
    on start {
        this.x = 1
    }
    on update(float dt) {
        this.x = this.x + dt
    }
"""
        prog = Parser.parse_source(src)
        self.assertEqual(len(prog.body), 1)
        members = prog.body[0].members
        names = [m.name for m in members]
        self.assertEqual(names, ["OnStart", "OnUpdate"])

    def test_if_else_braces(self):
        src = """
x = 1
if (x == 1) {
    y = 10
} else {
    y = 20
}
"""
        prog = Parser.parse_source(src)
        self.assertEqual(len(prog.body), 2)
        if_node = prog.body[1]
        self.assertTrue(if_node.else_body)

    def test_else_if_braces(self):
        src = """
x = 2
if (x == 1) {
    y = 1
} else if (x == 2) {
    y = 2
} else {
    y = 3
}
"""
        prog = Parser.parse_source(src)
        self.assertEqual(len(prog.body), 2)

    def test_actor_simple_syntax(self):
        src = """
actor player
on start {
    player.transform.position == x 0; y 0;
    player.ActorColor(#FFB74D)
    player.width set 48
    player.height = 48
}
"""
        prog = Parser.parse_source(src)
        self.assertEqual(prog.body[0].name, "player")
        self.assertEqual(prog.body[1].name, "OnStart")


class TestInterpreter(unittest.TestCase):
    def test_arithmetic(self):
        buf = io.StringIO()
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source('print.log(2 + 3 * 4)\n')
        self.assertIn("14", buf.getvalue())

    def test_if_else_braces_run(self):
        buf = io.StringIO()
        src = """
x = 2
if (x == 1) {
    print.log("then")
} else {
    print.log("else-ok")
}
"""
        with patch("sys.stdout", buf):
            Interpreter().run_source(src)
        self.assertIn("else-ok", buf.getvalue())
        self.assertNotIn("then", buf.getvalue())

    def test_typed_var_juxtaposed_initializer(self):
        """string name getinput(...) senza '=' deve salvare il valore."""
        buf = io.StringIO()
        src = """
string name getinput("n:")
print.log("HI-" + name)
"""
        with patch("builtins.input", return_value="andy"), patch("sys.stdout", buf):
            Interpreter().run_source(src)
        self.assertIn("HI-andy", buf.getvalue())

    def test_stile_del_tutorial(self):
        """Dichiarazioni senza '=', float con la f, risultati su print.output."""
        buf = io.StringIO()
        src = """
int vite 3
float velocita 2.5f
string titolo "livello 1"
bool vivo true

vite += 1
print.output("vite:", vite)
print.output("velocita:", velocita)
print.output("titolo:", titolo, vivo)
"""
        with patch("sys.stdout", buf):
            Interpreter().run_source(src)
        out = buf.getvalue()
        self.assertIn("vite: 4", out)
        self.assertIn("velocita: 2.5", out)
        self.assertIn("titolo: livello 1 true", out)

    def test_float_con_f_dentro_una_chiamata(self):
        """print.output("x:", 2.5f) non deve essere un errore di sintassi."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            Interpreter().run_source('print.output("x:", 2.5f, 90f)\n')
        self.assertIn("x: 2.5 90.0", buf.getvalue())

    def test_function(self):
        buf = io.StringIO()
        src = """
fun add(int a, int b)
    return int a + b

print.log(add(2, 5))
"""
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source(src)
        self.assertIn("7", buf.getvalue())

    def test_class_this(self):
        buf = io.StringIO()
        src = """
class Counter
    int n = 0
    fun bump()
        this.n = this.n + 1
        return this.n

c = Counter()
print.log(c.bump())
print.log(c.bump())
"""
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source(src)
        out = buf.getvalue()
        self.assertIn("1", out)
        self.assertIn("2", out)

    def test_while_for(self):
        buf = io.StringIO()
        src = """
int s = 0
int i = 0
while (i < 3)
    s = s + i
    i = i + 1
print.log(s)

int t = 0
for (j in range(0, 4))
    t = t + j
print.log(t)
"""
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source(src)
        lines = [ln for ln in buf.getvalue().strip().splitlines() if ln]
        self.assertEqual(lines[0], "3")
        self.assertEqual(lines[1], "6")

    def test_getinput_float_hint(self):
        interp = Interpreter()
        with patch("builtins.input", return_value="3.5"):
            interp.run_source('float x = getinput("n?" + f)\nprint.log(x)\n')
        # just ensure no crash; capture stdout
        buf = io.StringIO()
        with patch("builtins.input", return_value="3.5"), patch("sys.stdout", buf):
            interp2 = Interpreter()
            interp2.run_source('float x = getinput("n?" + f)\nprint.log(x)\n')
        self.assertIn("3.5", buf.getvalue())

    def test_time_import(self):
        interp = Interpreter()
        with patch("time.sleep") as sleep:
            interp.run_source("import time\ntime.breakcode(0.01)\n")
            sleep.assert_called()

    def test_random_import(self):
        buf = io.StringIO()
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source(
                "import random\nrandom.seed(1)\nprint.log(random.int(1, 1))\n"
            )
        self.assertIn("1", buf.getvalue())

    def test_screen_create_signature_parse(self):
        from cpython.parser import Parser

        prog = Parser.parse_source(
            'import screen\nscreen.create(800, 600, "title")\nscreen.create(fullscreen, "title")\n'
        )
        self.assertEqual(len(prog.body), 3)

    def test_math_and_json_libs(self):
        buf = io.StringIO()
        interp = Interpreter()
        with patch("sys.stdout", buf):
            interp.run_source(
                'import math\nimport json\nprint.log(math.clamp(15, 0, 10))\n'
                'print.log(json.encode({"a": 1}))\n'
            )
        out = buf.getvalue()
        self.assertIn("10", out)
        self.assertIn("a", out)

    def test_file_lib(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = (Path(tmp) / "t.txt").as_posix()
            buf = io.StringIO()
            interp = Interpreter()
            with patch("sys.stdout", buf):
                interp.run_source(
                    f'import file\nfile.write("{path}", "ciao")\nprint.log(file.read("{path}"))\n'
                )
            self.assertIn("ciao", buf.getvalue())

    def test_sdgame_module_loads(self):
        interp = Interpreter()
        interp.run_source("import sdgame\nimport audio\n")
        self.assertIn("sdgame", interp.module_cache)
        self.assertIn("audio", interp.module_cache)

    def test_jit_ir_emit_and_purity(self):
        from cpython.jit_ir import emit_function_ir, is_jittable_function
        from cpython.parser import Parser

        prog = Parser.parse_source(
            "fun add(int a, int b)\n    return int a + b\n"
        )
        fn = prog.body[0]
        self.assertTrue(is_jittable_function(fn))
        ir = emit_function_ir(fn)
        self.assertIn("fun add", ir)
        self.assertIn("rettype i64", ir)
        self.assertIn("= add a b", ir)

        bad = Parser.parse_source(
            'fun hello()\n    return string "x"\n'
        ).body[0]
        self.assertFalse(is_jittable_function(bad))

    def test_jit_backend_if_dll_present(self):
        from cpython.llvm_bridge import get_engine, jit_available

        if not jit_available():
            self.skipTest("DLL cpython_llvm non presente")
        eng = get_engine()
        self.assertIsNotNone(eng)
        buf = io.StringIO()
        interp = Interpreter(enable_jit=True)
        with patch("sys.stdout", buf):
            interp.run_source(
                "fun add(int a, int b)\n    return int a + b\nprint.log(add(2, 5))\n"
            )
        self.assertIn("7", buf.getvalue())
        # funzione deve essere stata compilata
        fn = interp.env.get("add")
        self.assertTrue(getattr(fn, "jit_ready", False))


if __name__ == "__main__":
    unittest.main()

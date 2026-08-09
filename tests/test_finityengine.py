"""Test per fixedupdate, getcollision e animazioni (senza aprire finestre)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
for extra in (str(ROOT), str(ROOT / "library")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import finityengine
from cpython import ast_nodes as ast
from cpython.interpreter import Interpreter
from cpython.lexer import Lexer
from cpython.parser import Parser


def _parse(src: str):
    return Parser(Lexer(src).tokenize()).parse()


class TestParserNewConstructs(unittest.TestCase):
    def test_on_fixedupdate_maps_to_handler(self):
        prog = _parse("on fixedupdate {\n    x = 1\n}\n")
        fn = prog.body[0]
        self.assertIsInstance(fn, ast.FunDef)
        self.assertEqual(fn.name, "OnFixedUpdate")
        self.assertEqual(fn.params, [("float", "dt")])

    def test_getcollision_without_parens_in_if(self):
        prog = _parse('if (getcollision "muro") {\n    x = 1\n}\n')
        cond = prog.body[0].condition
        self.assertIsInstance(cond, ast.Call)
        self.assertIsInstance(cond.callee, ast.Name)
        self.assertEqual(cond.callee.id, "getcollision")
        self.assertEqual(len(cond.args), 1)
        self.assertEqual(cond.args[0].value, "muro")

    def test_position_literal_not_broken(self):
        """x 380; y 280; deve restare una PositionLiteral, non una chiamata."""
        prog = _parse("player.transform.position == x 380; y 280;\n")
        self.assertTrue(
            any(isinstance(n, ast.PositionLiteral) for n in ast_walk(prog)),
            "PositionLiteral non trovata",
        )

    def test_juxtaposed_getinput_not_broken(self):
        buf = io.StringIO()
        src = 'string name getinput("n:")\nprint.log("HI-" + name)\n'
        with patch("builtins.input", return_value="andy"), patch("sys.stdout", buf):
            Interpreter().run_source(src)
        self.assertIn("HI-andy", buf.getvalue())


def ast_walk(node):
    yield node
    for value in vars(node).values():
        if isinstance(value, ast.Node):
            yield from ast_walk(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.Node):
                    yield from ast_walk(item)


class TestFixedStep(unittest.TestCase):
    def setUp(self):
        self.engine = finityengine.Engine()
        self.engine.Time.fixedDeltaTime = 0.02  # 50 Hz per conti facili

    def test_accumulates_steps(self):
        self.assertEqual(self.engine._advance_fixed(0.05), 2)  # resto 0.01
        self.assertEqual(self.engine._advance_fixed(0.01), 1)  # 0.01+0.01 = un passo

    def test_no_step_for_small_dt(self):
        self.assertEqual(self.engine._advance_fixed(0.005), 0)

    def test_lag_spike_is_clamped(self):
        steps = self.engine._advance_fixed(10.0)
        self.assertEqual(steps, self.engine.maxFixedSteps)
        self.assertEqual(self.engine._accumulator, 0.0)  # niente spirale della morte


class TestCollisions(unittest.TestCase):
    def setUp(self):
        self.engine = finityengine.Engine()
        self.player = finityengine.Actor("player")
        self.wall = finityengine.Actor("muro")
        self.engine.add_actor(self.player)
        self.engine.add_actor(self.wall)

    def test_overlapping_actors_marked(self):
        self.wall.transform.position.x = 10  # dentro il player 40x40
        self.engine._refresh_collisions()
        self.assertIn("muro", self.player._colliding)
        self.assertIn("player", self.wall._colliding)

    def test_distant_actors_not_marked(self):
        self.wall.transform.position.x = 500
        self.engine._refresh_collisions()
        self.assertFalse(self.player._colliding)
        self.assertFalse(self.wall._colliding)

    def test_get_collision_uses_current_actor(self):
        self.wall.transform.position.x = 10
        self.engine._refresh_collisions()
        old_engine = finityengine._engine
        finityengine._engine = self.engine
        try:
            self.engine._current_actor = self.player
            self.assertTrue(finityengine.get_collision("muro"))
            self.assertTrue(finityengine.get_collision("MURO"))  # case-insensitive
            self.assertTrue(finityengine.get_collision())  # senza nome: una qualsiasi
            self.assertFalse(finityengine.get_collision("nemico"))
            self.engine._current_actor = None
            self.assertFalse(finityengine.get_collision("muro"))
        finally:
            finityengine._engine = old_engine

    def test_getcollision_builtin_safe_without_engine(self):
        buf = io.StringIO()
        src = 'if (getcollision "muro") {\n    print.log("hit")\n}\nprint.log("done")\n'
        with patch("sys.stdout", buf):
            Interpreter().run_source(src)
        self.assertIn("done", buf.getvalue())
        self.assertNotIn("hit", buf.getvalue())


class TestAnimations(unittest.TestCase):
    def test_property_tween(self):
        actor = finityengine.Actor("a")
        actor.animate("x", 0, 100, 1)
        actor._advance_animations(0.5)
        self.assertAlmostEqual(actor.transform.position.x, 50.0)
        actor._advance_animations(0.5)
        self.assertAlmostEqual(actor.transform.position.x, 100.0)
        self.assertEqual(actor._tweens, [])  # finita: rimossa

    def test_tween_replaces_same_property(self):
        actor = finityengine.Actor("a")
        actor.animate("width", 0, 10, 1)
        actor.animate("width", 0, 999, 1)
        self.assertEqual(len(actor._tweens), 1)
        self.assertEqual(actor._tweens[0]["end"], 999.0)

    def test_animate_rejects_unknown_property(self):
        actor = finityengine.Actor("a")
        with self.assertRaises(ValueError):
            actor.animate("colore", 0, 1, 1)

    def test_frame_advance_with_fps(self):
        import pygame

        frames = [pygame.Surface((10, 10)) for _ in range(4)]
        actor = finityengine.Actor("a")
        actor._animations["run"] = {"frames": frames, "fps": 10.0}
        actor.play("run")
        self.assertIs(actor._current_frame(), frames[0])
        actor._advance_animations(0.1)  # 10 fps * 0.1s = frame 1
        self.assertIs(actor._current_frame(), frames[1])
        actor._advance_animations(0.35)  # frame 4.5 -> wrap a 0
        self.assertIs(actor._current_frame(), frames[0])
        actor.stop()
        self.assertIsNone(actor._current_frame())

    def test_play_requires_registered_animation(self):
        actor = finityengine.Actor("a")
        with self.assertRaises(ValueError):
            actor.play("run")

    def test_slice_sheet(self):
        import pygame

        sheet = pygame.Surface((60, 10))
        frames = finityengine._slice_sheet(sheet, 6)
        self.assertEqual(len(frames), 6)
        self.assertEqual(frames[0].get_size(), (10, 10))


class TestActorLifecycleBinding(unittest.TestCase):
    def test_on_fixedupdate_binds_to_actor(self):
        finityengine._engine.actors.clear()
        interp = Interpreter()
        interp.run_source("actor player\non fixedupdate {\n    player.move(1, 0)\n}\n")
        actor = finityengine._engine.actors[-1]
        self.assertIn("OnFixedUpdate", actor._handlers)
        finityengine._engine.actors.clear()


if __name__ == "__main__":
    unittest.main()

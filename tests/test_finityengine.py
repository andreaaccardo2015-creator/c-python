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
from cpython.errors import ParseError, RuntimeError_
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

    def test_animation_time_without_parens_in_if(self):
        prog = _parse('if (animation.time "2") {\n    x = 1\n}\n')
        cond = prog.body[0].condition
        self.assertIsInstance(cond, ast.Call)
        self.assertIsInstance(cond.callee, ast.Attribute)
        self.assertEqual(cond.callee.attr, "time")
        self.assertEqual(cond.args[0].value, "2")

    def test_module_call_with_parens_not_broken(self):
        """print.log("x") resta una chiamata normale, non una giustapposizione."""
        prog = _parse('print.log("ciao")\n')
        call = prog.body[0].expr
        self.assertIsInstance(call, ast.Call)
        self.assertEqual(len(call.args), 1)
        self.assertEqual(call.args[0].value, "ciao")

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


class TestCompoundAssignment(unittest.TestCase):
    """+= -= *= /= non esistevano: y += 5 dava un errore di sintassi."""

    def test_plus_equal_is_desugared(self):
        prog = _parse("int y = 1\ny += 5\n")
        assegna = prog.body[1]
        self.assertIsInstance(assegna, ast.Assign)
        self.assertIsInstance(assegna.value, ast.BinaryOp)
        self.assertEqual(assegna.value.op, "+")

    def test_all_four_operators_run(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            Interpreter().run_source(
                "int y = 10\ny += 5\ny *= 2\ny -= 4\ny /= 2\nprint.log(y)\n"
            )
        self.assertIn("13", buf.getvalue())


class TestAxisDeltaArguments(unittest.TestCase):
    """part("braccio", y += 5): asse e spostamento come singolo argomento."""

    def test_delta_argument_is_parsed(self):
        prog = _parse('player.rb.trasform.part("braccio", y += 5)\n')
        call = prog.body[0].expr
        self.assertEqual(len(call.args), 2)
        delta = call.args[1]
        self.assertIsInstance(delta, ast.AxisDelta)
        self.assertEqual(delta.axis, "y")
        self.assertEqual(delta.op, "+=")

    def test_absolute_and_negative_deltas(self):
        prog = _parse('p.part("gamba", x -= 2, z = 10)\n')
        args = prog.body[0].expr.args
        self.assertEqual([(a.axis, a.op) for a in args[1:]], [("x", "-="), ("z", "=")])

    def test_normal_arguments_still_work(self):
        prog = _parse('p.part("gamba", 5, 2 + 3)\n')
        args = prog.body[0].expr.args
        self.assertEqual(len(args), 3)
        self.assertFalse(any(isinstance(a, ast.AxisDelta) for a in args))

    def test_value_applies_relative_and_absolute(self):
        from cpython.values import AxisDelta

        self.assertEqual(AxisDelta("y", "+=", 5).apply(10), 15)
        self.assertEqual(AxisDelta("y", "-=", 5).apply(10), 5)
        self.assertEqual(AxisDelta("y", "=", 5).apply(10), 5)


class TestRigParts(unittest.TestCase):
    """rigidbody.call("RB") e lo spostamento delle parti del rig."""

    def setUp(self):
        finityengine._engine.actors.clear()
        self.addCleanup(finityengine._engine.actors.clear)

    def _esegui(self, corpo: str):
        interp = Interpreter()
        interp.run_source(f'actor player\nrigidbody.call("RB")\non start {{\n{corpo}\n}}\n')
        player = finityengine._engine.actors[-1]
        finityengine._engine._call_handler(player, "OnStart", [])
        return player

    def test_part_moves_immediately(self):
        player = self._esegui('    player.rb.trasform.part("braccio", y += 5)')
        self.assertEqual(player.part_offset("braccio"), {"y": 5.0})

    def test_alias_and_typo_are_case_insensitive(self):
        player = self._esegui('    player.RB.transform.part("braccio", y += 1)')
        self.assertEqual(player.part_offset("braccio", "y"), 1.0)

    def test_repeated_calls_accumulate(self):
        player = self._esegui('    player.rb.trasform.part("braccio", y += 5)')
        finityengine._engine._call_handler(player, "OnStart", [])
        self.assertEqual(player.part_offset("braccio", "y"), 10.0)

    def test_duration_interpolates_over_time(self):
        player = self._esegui('    player.rb.trasform.part("testa", y += 90, 0.5)')
        self.assertEqual(player.part_offset("testa"), {})
        player._advance_animations(0.25)
        self.assertAlmostEqual(player.part_offset("testa", "y"), 45.0)
        player._advance_animations(0.25)
        self.assertAlmostEqual(player.part_offset("testa", "y"), 90.0)
        self.assertEqual(player._part_tweens, [])

    def test_part_without_delta_is_rejected(self):
        actor = finityengine.Actor("a")
        with self.assertRaises(ValueError):
            finityengine.RigTransform(actor).part("braccio", 5)

    def test_unknown_part_reads_as_zero(self):
        self.assertEqual(finityengine.Actor("a").part_offset("mano", "y"), 0.0)


class TestComponentValidation(unittest.TestCase):
    """rigidbody.call e part() convalidati contro i bindings di FinityEngine.

    Senza handshake (bindings None, il caso di sempre) niente cambia: e' per
    questo che i test scritti prima di questa funzionalita' restano verdi.
    """

    def setUp(self):
        finityengine._engine.actors.clear()
        self.addCleanup(finityengine._engine.actors.clear)
        self.addCleanup(setattr, finityengine._engine, "bindings", None)

    def _bindings_con(self, components=(), rig_parts=(), nome="player"):
        from cpython.ipc import Bindings, EntityBinding

        return Bindings(
            entities={
                nome.lower(): EntityBinding(
                    components={c.lower() for c in components},
                    rig_parts={p.lower() for p in rig_parts},
                )
            }
        )

    def _esegui(self, corpo_globale: str, corpo_on_start: str | None = None):
        src = f'actor player\n{corpo_globale}\n'
        if corpo_on_start is not None:
            src += f'on start {{\n{corpo_on_start}\n}}\n'
        Interpreter().run_source(src)
        player = finityengine._engine.actors[-1]
        if corpo_on_start is not None:
            finityengine._engine._call_handler(player, "OnStart", [])
        return player

    def test_rigidbody_call_rejected_without_component(self):
        finityengine._engine.bindings = self._bindings_con(components=["transform"])
        with self.assertRaises(RuntimeError_) as ctx:
            self._esegui('rigidbody.call("RB")')
        self.assertIn("rigidbody", str(ctx.exception))

    def test_rigidbody_call_accepted_with_component(self):
        finityengine._engine.bindings = self._bindings_con(
            components=["transform", "rigidbody2d"]
        )
        self._esegui('rigidbody.call("RB")')  # non deve lanciare

    def test_missing_rig_part_is_rejected(self):
        finityengine._engine.bindings = self._bindings_con(
            components=["rigidbody"], rig_parts=["gamba"]
        )
        with self.assertRaises(RuntimeError_) as ctx:
            self._esegui(
                'rigidbody.call("RB")',
                'player.rb.trasform.part("braccio", y += 5)',
            )
        self.assertIn("braccio", str(ctx.exception))

    def test_known_rig_part_is_accepted(self):
        finityengine._engine.bindings = self._bindings_con(
            components=["rigidbody"], rig_parts=["braccio"]
        )
        player = self._esegui(
            'rigidbody.call("RB")',
            'player.rb.trasform.part("braccio", y += 5)',
        )
        self.assertEqual(player.part_offset("braccio", "y"), 5.0)

    def test_actor_not_in_scene_reports_clear_error(self):
        from cpython.ipc import Bindings

        finityengine._engine.bindings = Bindings(missing={"player": "not-found"})
        with self.assertRaises(RuntimeError_) as ctx:
            self._esegui('rigidbody.call("RB")')
        self.assertIn("non e' presente nella scena", str(ctx.exception))

    def test_ambiguous_actor_reports_clear_error(self):
        from cpython.ipc import Bindings

        finityengine._engine.bindings = Bindings(missing={"player": "ambiguous"})
        with self.assertRaises(RuntimeError_) as ctx:
            self._esegui('rigidbody.call("RB")')
        self.assertIn("ambiguo", str(ctx.exception))

    def test_error_gets_line_and_column_from_the_call_site(self):
        # actor player  -> riga 1
        # (riga vuota)  -> riga 2
        # rigidbody.call(...) -> riga 3
        finityengine._engine.bindings = self._bindings_con(components=["transform"])
        with self.assertRaises(RuntimeError_) as ctx:
            self._esegui('\nrigidbody.call("RB")')
        self.assertEqual(ctx.exception.line, 3)


class TestDuplicateHandlers(unittest.TestCase):
    """Uno stesso evento due volte sovrascriveva il primo senza dire niente."""

    def test_second_on_start_is_rejected(self):
        with self.assertRaises(ParseError) as ctx:
            _parse("on start {\n    x = 1\n}\non start {\n    y = 2\n}\n")
        messaggio = str(ctx.exception)
        self.assertIn("on start", messaggio)
        self.assertIn("riga 1", messaggio)

    def test_second_on_update_is_rejected(self):
        with self.assertRaises(ParseError):
            _parse("on update {\n    x = 1\n}\non update {\n    y = 2\n}\n")

    def test_different_events_are_fine(self):
        prog = _parse("on start {\n    x = 1\n}\non update {\n    y = 2\n}\n")
        self.assertEqual([n.name for n in prog.body], ["OnStart", "OnUpdate"])

    def test_new_actor_starts_a_new_scope(self):
        """Nel runtime standalone ogni actor porta i propri handler."""
        prog = _parse(
            "actor muro\non start {\n    x = 1\n}\n"
            "actor player\non start {\n    y = 2\n}\n"
        )
        self.assertEqual(len([n for n in prog.body if isinstance(n, ast.FunDef)]), 2)


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

    def test_play_does_not_restart_same_animation(self):
        """play() nell'on update non deve inchiodare il frame a 0 ogni giro."""
        import pygame

        actor = finityengine.Actor("a")
        actor._animations["run"] = {"frames": [pygame.Surface((4, 4))] * 3, "fps": 10.0}
        actor.play("run")
        actor._advance_animations(0.15)
        actor.play("run")
        self.assertAlmostEqual(actor._anim_frame, 1.5)


class TestAnimationModule(unittest.TestCase):
    """animation.start / animation.stop / animation.time "N" """

    def setUp(self):
        import pygame

        self.actor = finityengine.Actor("player")
        self.actor._animations["gira"] = {
            "frames": [pygame.Surface((4, 4))] * 3,
            "fps": 10.0,
        }
        finityengine._engine._current_actor = self.actor
        self.addCleanup(setattr, finityengine._engine, "_current_actor", None)

    def test_start_plays_animation(self):
        finityengine.animation_start("gira")
        self.assertEqual(self.actor._anim_name, "gira")

    def test_elapsed_seconds_follow_dt(self):
        finityengine.animation_start("gira")
        self.actor._advance_animations(0.5)
        self.assertAlmostEqual(self.actor.anim_elapsed(), 0.5)

    def test_time_is_true_only_after_the_threshold(self):
        finityengine.animation_start("gira")
        self.actor._advance_animations(1.9)
        self.assertFalse(finityengine.animation_time("2"))
        self.actor._advance_animations(0.2)
        self.assertTrue(finityengine.animation_time("2"))

    def test_stop_named_animation(self):
        finityengine.animation_start("gira")
        self.actor._advance_animations(2.1)
        finityengine.animation_stop("gira")
        self.assertIsNone(self.actor._anim_name)
        self.assertEqual(self.actor.anim_elapsed(), 0.0)
        self.assertFalse(finityengine.animation_time("2"))

    def test_stop_ignores_another_animation(self):
        finityengine.animation_start("gira")
        finityengine.animation_stop("camminata")
        self.assertEqual(self.actor._anim_name, "gira")

    def test_time_is_false_without_animation(self):
        self.assertFalse(finityengine.animation_time("0"))

    def test_module_is_available_to_scripts(self):
        interp = Interpreter()
        mod = interp.globals.get("animation")
        self.assertEqual(sorted(mod.attrs), ["start", "stop", "time"])


class TestAssetPaths(unittest.TestCase):
    """I path delle immagini seguono il file .cp, non la working directory."""

    def setUp(self):
        self._prev = finityengine._engine.script_dir
        self.addCleanup(setattr, finityengine._engine, "script_dir", self._prev)

    def test_relative_path_resolved_next_to_script(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            script_dir = Path(tmp)
            (script_dir / "assets").mkdir()
            asset = script_dir / "assets" / "hero.png"
            asset.write_bytes(b"")
            finityengine._engine.script_dir = script_dir
            self.assertEqual(
                Path(finityengine._resolve_asset("assets/hero.png")), asset
            )

    def test_absolute_path_is_kept(self):
        finityengine._engine.script_dir = Path("/qualsiasi")
        absolute = Path.cwd() / "logo.png"
        self.assertEqual(finityengine._resolve_asset(str(absolute)), str(absolute))

    def test_missing_asset_lists_attempted_paths(self):
        finityengine._engine.script_dir = Path("/base")
        with self.assertRaises(FileNotFoundError) as ctx:
            finityengine._resolve_asset("manca.png")
        self.assertIn("manca.png", str(ctx.exception))


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

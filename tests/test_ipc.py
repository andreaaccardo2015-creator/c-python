"""Test del modulo cpython.ipc: handshake ready/bindings con FinityEngine."""

from __future__ import annotations

import io
import json
import unittest

from cpython.ipc import Bindings, collect_actor_names, read_bindings, send_error, send_ready
from cpython.parser import Parser


def _parse(src: str):
    return Parser.parse_source(src)


class TestCollectActorNames(unittest.TestCase):
    def test_finds_names_in_order(self):
        prog = _parse("actor muro\non start {\n    x = 1\n}\nactor player\n")
        self.assertEqual(collect_actor_names(prog), ["muro", "player"])

    def test_deduplicates_same_actor(self):
        prog = _parse("actor player\non start {\n    x = 1\n}\nactor player\n")
        self.assertEqual(collect_actor_names(prog), ["player"])

    def test_empty_program_has_no_actors(self):
        prog = _parse("int x = 1\n")
        self.assertEqual(collect_actor_names(prog), [])


class TestSendPackets(unittest.TestCase):
    def test_send_ready_writes_one_json_line(self):
        buf = io.StringIO()
        send_ready(["player", "muro"], language_version="0.3.3", out=buf)
        line = buf.getvalue()
        self.assertTrue(line.endswith("\n"))
        packet = json.loads(line)
        self.assertEqual(packet["type"], "ready")
        self.assertEqual(packet["protocol"], 1)
        self.assertEqual(packet["actors"], ["player", "muro"])
        self.assertEqual(packet["languageVersion"], "0.3.3")

    def test_send_error_includes_location_when_given(self):
        buf = io.StringIO()
        send_error("problema", file="gioco.cpy", line=4, column=5, out=buf)
        packet = json.loads(buf.getvalue())
        self.assertEqual(
            packet,
            {
                "protocol": 1,
                "type": "error",
                "message": "problema",
                "file": "gioco.cpy",
                "line": 4,
                "column": 5,
            },
        )

    def test_send_error_omits_missing_location(self):
        buf = io.StringIO()
        send_error("problema", out=buf)
        packet = json.loads(buf.getvalue())
        self.assertEqual(packet, {"protocol": 1, "type": "error", "message": "problema"})


class TestBindingsFromPacket(unittest.TestCase):
    def test_entities_and_missing_are_lowercased(self):
        packet = {
            "protocol": 1,
            "type": "bindings",
            "entities": [
                {
                    "scriptName": "Player",
                    "entityId": "uuid-1",
                    "dimension": "3d",
                    "kind": "mesh",
                    "components": ["Transform", "RigidBody"],
                    "rigParts": ["Braccio", "Gamba"],
                }
            ],
            "missing": [{"scriptName": "Nemico", "reason": "not-found"}],
        }
        bindings = Bindings.from_packet(packet)
        binding = bindings.get("player")
        self.assertIsNotNone(binding)
        self.assertTrue(binding.has_component("rigidbody"))
        self.assertTrue(binding.has_rig_part("braccio"))
        self.assertFalse(binding.has_rig_part("testa"))
        self.assertEqual(bindings.reason_for_missing("NEMICO"), "not-found")
        self.assertIsNone(bindings.get("nemico"))

    def test_rigidbody2d_matches_rigidbody_prefix(self):
        bindings = Bindings.from_packet(
            {"entities": [{"scriptName": "sprite", "components": ["rigidbody2d"]}]}
        )
        self.assertTrue(bindings.get("sprite").has_component("rigidbody"))


class TestReadBindings(unittest.TestCase):
    def test_valid_bindings_line_is_parsed(self):
        packet = {
            "protocol": 1,
            "type": "bindings",
            "entities": [{"scriptName": "player", "components": ["rigidbody"]}],
            "missing": [],
        }
        stream = io.StringIO(json.dumps(packet) + "\n")
        bindings = read_bindings(timeout=2.0, in_stream=stream)
        self.assertIsNotNone(bindings)
        self.assertTrue(bindings.get("player").has_component("rigidbody"))

    def test_empty_stream_times_out_to_none(self):
        stream = io.StringIO("")
        self.assertIsNone(read_bindings(timeout=0.2, in_stream=stream))

    def test_wrong_packet_type_is_ignored(self):
        stream = io.StringIO(json.dumps({"type": "hello"}) + "\n")
        self.assertIsNone(read_bindings(timeout=0.2, in_stream=stream))

    def test_invalid_json_is_ignored(self):
        stream = io.StringIO("non e' json\n")
        self.assertIsNone(read_bindings(timeout=0.2, in_stream=stream))


if __name__ == "__main__":
    unittest.main()

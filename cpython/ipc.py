"""Handshake ready/bindings con FinityEngine (Electron) via stdio.

Protocollo concordato con il lato FinityEngine: CPython legge gli ``actor``
dichiarati nello script e li annuncia con un pacchetto ``ready``; FinityEngine
risponde con ``bindings``, l'elenco dei componenti e delle parti del rig
realmente presenti sui modelli della scena. Da quel momento in poi
``rigidbody.call(...)`` e ``part(...)`` vengono convalidati contro questi dati.

Non e' un requisito per l'uso standalone di ``cpy run``: se il processo non
viene lanciato con ``--ipc-stdio``, o se FinityEngine non risponde in tempo,
il gioco parte comunque, semplicemente senza questa convalida — esattamente
come si e' sempre comportato.
"""

from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass, field
from typing import IO, Any

from . import ast_nodes as ast

PROTOCOL = 1


@dataclass
class EntityBinding:
    """Un'entita' della scena, cosi' come descritta da FinityEngine."""

    entity_id: str = ""
    dimension: str = ""
    kind: str = ""
    name: str = ""
    tag: str = ""
    components: set[str] = field(default_factory=set)
    rig_parts: set[str] = field(default_factory=set)

    def has_component(self, *prefixes: str) -> bool:
        """rigidbody.call deve accettare sia 'rigidbody' che 'rigidbody2d'."""
        return any(c.startswith(prefixes) for c in self.components)

    def has_rig_part(self, name: str) -> bool:
        return str(name).lower() in self.rig_parts


@dataclass
class Bindings:
    """Risultato del pacchetto ``bindings`` inviato da FinityEngine."""

    entities: dict[str, EntityBinding] = field(default_factory=dict)  # scriptName minuscolo
    missing: dict[str, str] = field(default_factory=dict)  # scriptName minuscolo -> motivo

    def get(self, script_name: str) -> EntityBinding | None:
        return self.entities.get(str(script_name).lower())

    def reason_for_missing(self, script_name: str) -> str | None:
        return self.missing.get(str(script_name).lower())

    @classmethod
    def from_packet(cls, packet: dict[str, Any]) -> "Bindings":
        entities: dict[str, EntityBinding] = {}
        for e in packet.get("entities", []) or []:
            name = str(e.get("scriptName", "")).strip()
            if not name:
                continue
            entities[name.lower()] = EntityBinding(
                entity_id=str(e.get("entityId", "")),
                dimension=str(e.get("dimension", "")),
                kind=str(e.get("kind", "")),
                name=str(e.get("name", "")),
                tag=str(e.get("tag", "")),
                components={str(c).lower() for c in e.get("components", []) or []},
                rig_parts={str(p).lower() for p in e.get("rigParts", []) or []},
            )
        missing = {
            str(m.get("scriptName", "")).strip().lower(): str(m.get("reason", "unknown"))
            for m in packet.get("missing", []) or []
            if m.get("scriptName")
        }
        return cls(entities=entities, missing=missing)


def collect_actor_names(program: ast.Program) -> list[str]:
    """Nomi degli 'actor NAME' dichiarati nel programma, in ordine di apparizione."""
    names: list[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, ast.ActorDecl):
            key = node.name.lower()
            if key not in seen:
                seen.add(key)
                names.append(node.name)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if isinstance(node, ast.Node):
            for value in vars(node).values():
                walk(value)

    walk(program.body)
    return names


def send_ready(actors: list[str], *, language_version: str, out: IO[str] = sys.stdout) -> None:
    packet = {
        "protocol": PROTOCOL,
        "type": "ready",
        "languageVersion": language_version,
        "actors": list(actors),
    }
    out.write(json.dumps(packet) + "\n")
    out.flush()


def send_error(
    message: str,
    *,
    file: str = "",
    line: int | None = None,
    column: int | None = None,
    out: IO[str] = sys.stdout,
) -> None:
    packet: dict[str, Any] = {"protocol": PROTOCOL, "type": "error", "message": message}
    if file:
        packet["file"] = file
    if line is not None:
        packet["line"] = line
    if column is not None:
        packet["column"] = column
    out.write(json.dumps(packet) + "\n")
    out.flush()


def read_bindings(*, timeout: float = 5.0, in_stream: IO[str] = sys.stdin) -> Bindings | None:
    """Legge la prima riga JSON di tipo 'bindings' da stdin, con un timeout.

    Ritorna None se scade il tempo, se lo stream si chiude o se la riga non e'
    valida: in tutti questi casi la convalida viene semplicemente saltata,
    cosi' un editor non ancora pronto (o l'esecuzione da terminale) non
    blocca mai il gioco.
    """
    result: dict[str, str] = {}

    def _read() -> None:
        try:
            result["line"] = in_stream.readline()
        except Exception:
            result["line"] = ""

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive() or not result.get("line", "").strip():
        return None
    try:
        packet = json.loads(result["line"])
    except ValueError:
        return None
    if not isinstance(packet, dict) or packet.get("type") != "bindings":
        return None
    return Bindings.from_packet(packet)

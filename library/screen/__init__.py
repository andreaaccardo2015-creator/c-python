"""Libreria screen — creazione finestra di gioco."""

from __future__ import annotations

from typing import Any


FULLSCREEN = "fullscreen"


def create(*args: Any) -> None:
    """
    screen.create(800, 600, "titolo")
    screen.create(fullscreen, "titolo")
    screen.create("fullscreen", "titolo")
    """
    from finityengine import create_screen

    if len(args) == 2:
        mode, title = args
        if _is_fullscreen(mode):
            create_screen(title=str(title), fullscreen=True)
            return
        raise TypeError(
            'Usa screen.create(fullscreen, "titolo") oppure screen.create(800, 600, "titolo")'
        )
    if len(args) == 3:
        width, height, title = args
        if _is_fullscreen(width):
            create_screen(title=str(title), fullscreen=True)
            return
        create_screen(int(width), int(height), str(title), fullscreen=False)
        return
    raise TypeError(
        'screen.create vuole (larghezza, altezza, titolo) oppure (fullscreen, titolo)'
    )


def _is_fullscreen(value: Any) -> bool:
    if value is FULLSCREEN:
        return True
    if isinstance(value, str) and value.lower() == "fullscreen":
        return True
    return False


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    # costante globale fullscreen per screen.create(fullscreen, "...")
    interpreter.globals.define("fullscreen", FULLSCREEN)

    return NativeModule(
        "screen",
        {
            "create": NativeFunction("create", create),
            "fullscreen": FULLSCREEN,
        },
    )

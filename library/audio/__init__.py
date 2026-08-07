"""Libreria audio — suoni e musica (pygame.mixer)."""

from __future__ import annotations

from typing import Any, Optional

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None  # type: ignore

_initialized = False
_music_path: Optional[str] = None


def _ensure() -> None:
    global _initialized
    if pygame is None:
        raise RuntimeError("pygame non installato. Esegui: pip install pygame")
    if not _initialized:
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        _initialized = True


def play(path: Any, volume: Any = 1.0) -> None:
    """Riproduce un effetto sonoro (non blocca)."""
    _ensure()
    sound = pygame.mixer.Sound(str(path))
    sound.set_volume(max(0.0, min(1.0, float(volume))))
    sound.play()


def music(path: Any, loop: Any = True, volume: Any = 0.7) -> None:
    """Avvia musica di sottofondo."""
    global _music_path
    _ensure()
    _music_path = str(path)
    pygame.mixer.music.load(_music_path)
    pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
    pygame.mixer.music.play(-1 if bool(loop) else 0)


def stop_music() -> None:
    _ensure()
    pygame.mixer.music.stop()


def pause_music() -> None:
    _ensure()
    pygame.mixer.music.pause()


def resume_music() -> None:
    _ensure()
    pygame.mixer.music.unpause()


def set_volume(volume: Any) -> None:
    _ensure()
    pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "audio",
        {
            "play": NativeFunction("play", play),
            "music": NativeFunction("music", music),
            "stop_music": NativeFunction("stop_music", stop_music),
            "pause_music": NativeFunction("pause_music", pause_music),
            "resume_music": NativeFunction("resume_music", resume_music),
            "set_volume": NativeFunction("set_volume", set_volume),
        },
    )

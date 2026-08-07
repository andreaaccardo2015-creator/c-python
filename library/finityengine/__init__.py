"""FinityEngine — game engine 2D per C Python, centrato sugli Actor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from cpython.interpreter import Interpreter

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None  # type: ignore


def _parse_color(color: Any) -> tuple[int, int, int]:
    if isinstance(color, tuple) and len(color) >= 3:
        return int(color[0]), int(color[1]), int(color[2])
    if isinstance(color, int):
        return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
    if isinstance(color, str):
        s = color.strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        value = int(s, 16)
        return _parse_color(value)
    raise TypeError(f"Colore non valido: {color!r}")


class Position:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        return f"x {self.x}; y {self.y}"


class Transform:
    def __init__(self):
        self.position = Position(0, 0)

    def move(self, dx: float, dy: float) -> None:
        self.position.x += float(dx)
        self.position.y += float(dy)


class Actor:
    """Oggetto di gioco a cui è sempre collegato lo script."""

    def __init__(self, name: str):
        self.name = name
        self.transform = Transform()
        self.trasform = self.transform  # alias (typo accettato)
        self.width = 40.0
        self.height = 40.0
        self.color = (80, 180, 255)
        self.active = True
        self._started = False
        self._handlers: dict[str, Any] = {}
        self._interpreter: Any = None
        # collisioni precompilate: sync automatico con width/height
        self._collider_enabled = True

    def ActorColor(self, color: Any) -> None:
        self.color = _parse_color(color)

    def move(self, dx: float, dy: float) -> None:
        self.transform.move(dx, dy)

    def bind_handler(self, name: str, function: Any, interpreter: Any) -> None:
        self._handlers[name] = function
        self._interpreter = interpreter


class _Input:
    def __init__(self, engine: "Engine"):
        self._engine = engine

    def GetKey(self, key: str) -> bool:
        if pygame is None:
            return False
        keys = pygame.key.get_pressed()
        code = self._key_code(key)
        return bool(keys[code]) if code is not None else False

    def GetKeyDown(self, key: str) -> bool:
        return key.lower() in self._engine._keys_down

    def _key_code(self, key: str):
        if pygame is None:
            return None
        mapping = {
            "w": pygame.K_w,
            "a": pygame.K_a,
            "s": pygame.K_s,
            "d": pygame.K_d,
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "space": pygame.K_SPACE,
            "escape": pygame.K_ESCAPE,
            "return": pygame.K_RETURN,
            "enter": pygame.K_RETURN,
        }
        return mapping.get(key.lower())


class _Time:
    def __init__(self):
        self.deltaTime = 0.0
        self.time = 0.0


class Engine:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.title = "FinityEngine"
        self.actors: list[Actor] = []
        self._running = False
        self._screen = None
        self._clock = None
        self._keys_down: set[str] = set()
        self.Input = _Input(self)
        self.Time = _Time()
        self.background = (24, 28, 36)

    def Init(
        self,
        width: int = 800,
        height: int = 600,
        title: str = "FinityEngine",
        *,
        fullscreen: bool = False,
    ) -> None:
        if pygame is None:
            raise RuntimeError("pygame non installato. Esegui: pip install pygame")
        self.title = str(title)
        self.fullscreen = bool(fullscreen)
        pygame.init()
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        if self.fullscreen:
            info = pygame.display.Info()
            self.width = int(info.current_w)
            self.height = int(info.current_h)
            self._screen = pygame.display.set_mode((0, 0), flags)
        else:
            self.width = int(width)
            self.height = int(height)
            self._screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption(self.title)
        self._clock = pygame.time.Clock()

    def add_actor(self, actor: Actor) -> Actor:
        self.actors.append(actor)
        return actor

    def Run(self) -> None:
        if pygame is None or self._screen is None:
            self.Init(self.width, self.height, self.title)
        assert self._clock is not None
        assert self._screen is not None
        self._running = True

        while self._running:
            dt = self._clock.tick(60) / 1000.0
            self.Time.deltaTime = dt
            self.Time.time += dt
            self._keys_down.clear()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    self._keys_down.add(pygame.key.name(event.key))

            for actor in list(self.actors):
                if not actor.active:
                    continue
                if not actor._started:
                    actor._started = True
                    self._call_handler(actor, "OnStart", [])
                self._call_handler(actor, "OnUpdate", [dt])

            # collisioni precompilate (AABB da width/height)
            for i, a in enumerate(self.actors):
                if not a.active or not a._collider_enabled:
                    continue
                for b in self.actors[i + 1 :]:
                    if not b.active or not b._collider_enabled:
                        continue
                    if self._overlaps(a, b):
                        self._call_handler(a, "OnCollision", [b])
                        self._call_handler(b, "OnCollision", [a])

            self._screen.fill(self.background)
            for actor in self.actors:
                if actor.active:
                    self._draw_actor(actor)
            pygame.display.flip()

        pygame.quit()

    def _overlaps(self, a: Actor, b: Actor) -> bool:
        ax, ay = a.transform.position.x, a.transform.position.y
        bx, by = b.transform.position.x, b.transform.position.y
        return (
            ax < bx + b.width
            and ax + a.width > bx
            and ay < by + b.height
            and ay + a.height > by
        )

    def _call_handler(self, actor: Actor, name: str, args: list) -> None:
        from cpython.values import Function

        fn = actor._handlers.get(name)
        interp = actor._interpreter
        if fn is None or interp is None:
            return
        if isinstance(fn, Function):
            interp._call_function(fn, args, this=None)
        elif callable(fn):
            fn(*args)

    def _draw_actor(self, actor: Actor) -> None:
        assert self._screen is not None and pygame is not None
        pos = actor.transform.position
        rect = pygame.Rect(int(pos.x), int(pos.y), int(actor.width), int(actor.height))
        pygame.draw.rect(self._screen, actor.color, rect)


_engine = Engine()


def create_screen(width=800, height=600, title: str = "FinityEngine", fullscreen: bool = False) -> None:
    """Usato da screen.create — apre la finestra di gioco."""
    _engine.Init(width, height, title, fullscreen=fullscreen)


def Run() -> None:
    _engine.Run()


def create_actor(name: str, interpreter: "Interpreter") -> Actor:
    actor = Actor(name)
    _engine.add_actor(actor)
    interpreter.env.define(name, actor)
    interpreter.current_actor = actor
    return actor


def create_cp_module(interpreter: "Interpreter"):
    from cpython.values import NativeFunction, NativeModule

    def actor_fn(name: str):
        return create_actor(str(name), interpreter)

    attrs = {
        "Run": NativeFunction("Run", Run),
        "Actor": NativeFunction("Actor", actor_fn),
        "Input": _engine.Input,
        "Time": _engine.Time,
        "Engine": _engine,
    }
    return NativeModule("finityengine", attrs)

"""FinityEngine — game engine 2D per C Python, centrato sugli Actor."""

from __future__ import annotations

from pathlib import Path
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


_image_cache: dict[str, Any] = {}


def _resolve_asset(path: str) -> str:
    """Percorso di un'immagine, cercata accanto allo script prima che nella CWD.

    Chi scrive un .cp ragiona in percorsi relativi al proprio file, non alla
    cartella da cui viene lanciato ``cpy run``.
    """
    p = Path(path)
    if p.is_absolute():
        return str(p)
    tried = []
    base = _engine.script_dir
    if base is not None:
        candidate = base / p
        if candidate.is_file():
            return str(candidate)
        tried.append(str(candidate))
    if p.is_file():
        return str(p)
    tried.append(str(p.resolve()))
    raise FileNotFoundError("Immagine non trovata. Percorsi provati: " + ", ".join(tried))


def _load_image(path: str) -> Any:
    """Carica un'immagine (con cache per path, cosi' lo stesso file non viene riletto)."""
    if pygame is None:
        raise RuntimeError("pygame non installato. Esegui: pip install pygame")
    path = _resolve_asset(path)
    surf = _image_cache.get(path)
    if surf is None:
        surf = pygame.image.load(path)
        try:
            surf = surf.convert_alpha()
        except pygame.error:
            pass  # display non ancora inizializzato: la surface raw va bene
        _image_cache[path] = surf
    return surf


def _slice_sheet(sheet: Any, count: int) -> list[Any]:
    """Taglia uno sprite sheet orizzontale in `count` frame uguali."""
    w = sheet.get_width() // count
    h = sheet.get_height()
    return [sheet.subsurface(pygame.Rect(i * w, 0, w, h)) for i in range(count)]


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
        # nomi (lowercase) degli actor attualmente sovrapposti — per getcollision
        self._colliding: set[str] = set()
        # sprite/animazioni
        self._sprite_frames: list[Any] = []
        self._animations: dict[str, dict[str, Any]] = {}
        self._anim_name: str | None = None
        self._anim_frame = 0.0
        self._tweens: list[dict[str, Any]] = []
        # parti del rig spostate dallo script: nome parte -> asse -> offset
        self._parts: dict[str, dict[str, float]] = {}
        self._part_tweens: list[dict[str, Any]] = []

    def ActorColor(self, color: Any) -> None:
        self.color = _parse_color(color)

    def move(self, dx: float, dy: float) -> None:
        self.transform.move(dx, dy)

    def bind_handler(self, name: str, function: Any, interpreter: Any) -> None:
        self._handlers[name] = function
        self._interpreter = interpreter

    # ---- sprite e animazioni ----

    def sprite(self, path: Any) -> None:
        """player.sprite("hero.png") — immagine al posto del rettangolo."""
        self._sprite_frames = [_load_image(str(path))]
        self._anim_name = None

    def animation(self, name: Any, path: Any, frames: Any, fps: Any = 12) -> None:
        """player.animation("run", "run.png", 6, 12) — sprite sheet orizzontale."""
        count = int(frames)
        if count < 1:
            raise ValueError("animation: il numero di frame deve essere >= 1")
        sheet = _load_image(str(path))
        self._animations[str(name).lower()] = {
            "frames": _slice_sheet(sheet, count),
            "fps": float(fps),
        }

    def play(self, name: Any) -> None:
        """player.play("run") — avvia un'animazione registrata."""
        key = str(name).lower()
        if key not in self._animations:
            raise ValueError(
                f"Animazione '{name}' non registrata: usa prima actor.animation(...)"
            )
        if self._anim_name != key:
            self._anim_name = key
            self._anim_frame = 0.0

    def stop(self) -> None:
        """player.stop() — ferma l'animazione corrente."""
        self._anim_name = None
        self._anim_frame = 0.0

    def animate(self, prop: Any, start: Any, end: Any, duration: Any) -> None:
        """player.animate("x", 100, 400, 2) — interpola una proprieta' in N secondi."""
        key = str(prop).lower()
        if key not in ("x", "y", "width", "height"):
            raise ValueError("animate supporta: x, y, width, height")
        self._tweens = [t for t in self._tweens if t["prop"] != key]
        self._tweens.append(
            {
                "prop": key,
                "start": float(start),
                "end": float(end),
                "duration": max(float(duration), 1e-6),
                "elapsed": 0.0,
            }
        )

    def _advance_animations(self, dt: float) -> None:
        if self._anim_name:
            self._anim_frame += self._animations[self._anim_name]["fps"] * dt
        for t in self._tweens:
            t["elapsed"] = min(t["elapsed"] + dt, t["duration"])
            k = t["elapsed"] / t["duration"]
            self._set_prop(t["prop"], t["start"] + (t["end"] - t["start"]) * k)
        self._tweens = [t for t in self._tweens if t["elapsed"] < t["duration"]]
        for t in self._part_tweens:
            t["elapsed"] = min(t["elapsed"] + dt, t["duration"])
            k = t["elapsed"] / t["duration"]
            self._parts.setdefault(t["part"], {})[t["axis"]] = (
                t["start"] + (t["end"] - t["start"]) * k
            )
        self._part_tweens = [t for t in self._part_tweens if t["elapsed"] < t["duration"]]

    # ---- parti del rig ----

    def move_part(self, name: Any, deltas: list, duration: float = 0.0) -> None:
        """Sposta una parte del modello, subito o gradualmente in `duration` secondi."""
        _validate_rig_part(self, name)
        parte = str(name).lower()
        offsets = self._parts.setdefault(parte, {})
        for delta in deltas:
            axis = str(delta.axis).lower()
            partenza = offsets.get(axis, 0.0)
            arrivo = delta.apply(partenza)
            if duration <= 0:
                offsets[axis] = arrivo
                continue
            # un solo movimento per volta sullo stesso asse della stessa parte
            self._part_tweens = [
                t
                for t in self._part_tweens
                if not (t["part"] == parte and t["axis"] == axis)
            ]
            self._part_tweens.append(
                {
                    "part": parte,
                    "axis": axis,
                    "start": partenza,
                    "end": arrivo,
                    "duration": max(float(duration), 1e-6),
                    "elapsed": 0.0,
                }
            )

    def part_offset(self, name: Any, axis: Any = None) -> Any:
        """Spostamento accumulato di una parte: tutti gli assi, o uno solo."""
        offsets = self._parts.get(str(name).lower(), {})
        if axis is None:
            return dict(offsets)
        return offsets.get(str(axis).lower(), 0.0)

    def _set_prop(self, prop: str, value: float) -> None:
        if prop == "x":
            self.transform.position.x = value
        elif prop == "y":
            self.transform.position.y = value
        elif prop == "width":
            self.width = value
        elif prop == "height":
            self.height = value

    def anim_elapsed(self) -> float:
        """Secondi dall'inizio dell'animazione in corso (0 se non ne gira nessuna).

        Non serve un contatore in piu': _anim_frame cresce di fps*dt, quindi
        dividerlo per gli fps restituisce esattamente il tempo trascorso.
        """
        if not self._anim_name:
            return 0.0
        fps = self._animations[self._anim_name]["fps"]
        return self._anim_frame / fps if fps else 0.0

    def _current_frame(self) -> Any:
        if self._anim_name:
            frames = self._animations[self._anim_name]["frames"]
            return frames[int(self._anim_frame) % len(frames)]
        if self._sprite_frames:
            return self._sprite_frames[0]
        return None


class RigTransform:
    """Il transform di un rigidbody: agisce sulle parti nominate del modello."""

    def __init__(self, actor: Actor):
        self._actor = actor

    def part(self, name: Any, *args: Any) -> None:
        """part("braccio", y += 5) — o con la durata: part("braccio", y += 5, 0.5)"""
        from cpython.values import AxisDelta

        deltas = [a for a in args if isinstance(a, AxisDelta)]
        if not deltas:
            raise ValueError(
                'part: serve almeno uno spostamento su un asse, es. part("braccio", y += 5)'
            )
        resto = [a for a in args if not isinstance(a, AxisDelta)]
        duration = float(resto[0]) if resto else 0.0
        self._actor.move_part(name, deltas, duration)


class RigidBody:
    """Quello che restituisce rigidbody.call("RB")."""

    def __init__(self, actor: Actor, alias: str):
        self.alias = alias
        self._actor = actor
        self.transform = RigTransform(actor)
        self.trasform = self.transform  # alias (typo accettato)


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
        # passo dell'OnFixedUpdate (secondi): costante, indipendente dagli FPS
        self.fixedDeltaTime = 1.0 / 60.0


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
        # fixed timestep
        self._accumulator = 0.0
        self.maxFixedSteps = 5
        # actor il cui handler e' in esecuzione (per getcollision)
        self._current_actor: Actor | None = None
        # cartella dello script .cp: base per i percorsi delle immagini
        self.script_dir: Path | None = None
        # ultimo actor dichiarato: rigidbody.call() sta fuori dagli handler
        self._declared_actor: Actor | None = None
        # esito dell'handshake ready/bindings con FinityEngine (None = non
        # ancora avvenuto, o non richiesto: nessuna convalida in quel caso)
        self.bindings: Any = None

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
                if actor.active and not actor._started:
                    actor._started = True
                    self._call_handler(actor, "OnStart", [])

            # Passi fissi: OnFixedUpdate a frequenza costante (fisica),
            # indipendente dagli FPS. Prima del variabile, come in Unity.
            fixed_dt = self.Time.fixedDeltaTime
            for _ in range(self._advance_fixed(dt)):
                self._refresh_collisions()
                for actor in list(self.actors):
                    if actor.active:
                        self._call_handler(actor, "OnFixedUpdate", [fixed_dt])

            self._refresh_collisions()
            for actor in list(self.actors):
                if actor.active:
                    self._call_handler(actor, "OnUpdate", [dt])

            # collisioni precompilate (AABB da width/height): eventi on collision
            for a, b in self._refresh_collisions():
                self._call_handler(a, "OnCollision", [b])
                self._call_handler(b, "OnCollision", [a])

            for actor in self.actors:
                if actor.active:
                    actor._advance_animations(dt)

            self._screen.fill(self.background)
            for actor in self.actors:
                if actor.active:
                    self._draw_actor(actor)
            pygame.display.flip()

        pygame.quit()

    def _advance_fixed(self, dt: float) -> int:
        """Accumula dt e ritorna quanti passi fissi eseguire in questo frame."""
        self._accumulator += dt
        steps = 0
        while self._accumulator >= self.Time.fixedDeltaTime and steps < self.maxFixedSteps:
            self._accumulator -= self.Time.fixedDeltaTime
            steps += 1
        if steps >= self.maxFixedSteps:
            self._accumulator = 0.0  # dopo un lag lungo non recuperare all'infinito
        return steps

    def _refresh_collisions(self) -> list[tuple[Actor, Actor]]:
        """Ricalcola gli insiemi di collisione per actor; ritorna le coppie sovrapposte."""
        for actor in self.actors:
            actor._colliding.clear()
        pairs: list[tuple[Actor, Actor]] = []
        for i, a in enumerate(self.actors):
            if not a.active or not a._collider_enabled:
                continue
            for b in self.actors[i + 1 :]:
                if not b.active or not b._collider_enabled:
                    continue
                if self._overlaps(a, b):
                    a._colliding.add(b.name.lower())
                    b._colliding.add(a.name.lower())
                    pairs.append((a, b))
        return pairs

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
        prev = self._current_actor
        self._current_actor = actor
        try:
            if isinstance(fn, Function):
                interp._call_function(fn, args, this=None)
            elif callable(fn):
                fn(*args)
        finally:
            self._current_actor = prev

    def _draw_actor(self, actor: Actor) -> None:
        assert self._screen is not None and pygame is not None
        pos = actor.transform.position
        frame = actor._current_frame()
        if frame is not None:
            size = (max(int(actor.width), 1), max(int(actor.height), 1))
            if frame.get_size() != size:
                frame = pygame.transform.scale(frame, size)
            self._screen.blit(frame, (int(pos.x), int(pos.y)))
            return
        rect = pygame.Rect(int(pos.x), int(pos.y), int(actor.width), int(actor.height))
        pygame.draw.rect(self._screen, actor.color, rect)


_engine = Engine()


def create_screen(width=800, height=600, title: str = "FinityEngine", fullscreen: bool = False) -> None:
    """Usato da screen.create — apre la finestra di gioco."""
    _engine.Init(width, height, title, fullscreen=fullscreen)


def Run() -> None:
    _engine.Run()


def _track_script_dir(interpreter: "Interpreter") -> None:
    filename = getattr(interpreter, "filename", None)
    if filename:
        _engine.script_dir = Path(filename).resolve().parent


def create_actor(name: str, interpreter: "Interpreter") -> Actor:
    _track_script_dir(interpreter)
    actor = Actor(name)
    _engine._declared_actor = actor
    _engine.add_actor(actor)
    interpreter.env.define(name, actor)
    interpreter.current_actor = actor
    return actor


def get_collision(name: Any = None) -> bool:
    """Builtin getcollision: l'actor dello script corrente tocca 'name'?

    Senza argomento ritorna True se tocca un actor qualsiasi.
    """
    actor = _engine._current_actor
    if actor is None:
        return False
    if name is None:
        return bool(actor._colliding)
    return str(name).lower() in actor._colliding


def animation_start(name: Any) -> None:
    """animation.start("camminata") — avvia un'animazione del modello corrente."""
    actor = _engine._current_actor
    if actor is not None:
        actor.play(name)


def animation_stop(name: Any = None) -> None:
    """animation.stop("camminata") — ferma quell'animazione, se e' quella in corso."""
    actor = _engine._current_actor
    if actor is None:
        return
    if name is None or str(name).lower() == actor._anim_name:
        actor.stop()


def animation_time(seconds: Any) -> bool:
    """if (animation.time "2") — l'animazione in corso ha raggiunto i 2 secondi?"""
    actor = _engine._current_actor
    if actor is None or not actor._anim_name:
        return False
    return actor.anim_elapsed() >= float(seconds)


def set_bindings(bindings: Any) -> None:
    """Salva l'esito dell'handshake ready/bindings (o None se non c'e' stato)."""
    _engine.bindings = bindings


def _binding_error(message: str) -> Any:
    from cpython.errors import RuntimeError_

    return RuntimeError_(message)


def _binding_for(actor: Actor) -> Any:
    """La entita' della scena per questo actor, o solleva un errore chiaro.

    None se non abbiamo mai fatto l'handshake (uso standalone): in quel caso
    la convalida e' semplicemente saltata, come sempre.
    """
    bindings = _engine.bindings
    if bindings is None:
        return None
    binding = bindings.get(actor.name)
    if binding is not None:
        return binding
    reason = bindings.reason_for_missing(actor.name)
    if reason == "ambiguous":
        raise _binding_error(
            f"'{actor.name}' e' ambiguo nella scena: piu' oggetti hanno questo nome"
        )
    raise _binding_error(f"Il modello '{actor.name}' non e' presente nella scena")


def _validate_component(actor: Actor, *prefixes: str) -> None:
    binding = _binding_for(actor)
    if binding is None:
        return
    if not binding.has_component(*prefixes):
        opzioni = "' o '".join(prefixes)
        raise _binding_error(f"Il modello '{actor.name}' non ha un componente '{opzioni}'")


def _validate_rig_part(actor: Actor, name: Any) -> None:
    binding = _binding_for(actor)
    if binding is None:
        return
    if not binding.has_rig_part(name):
        raise _binding_error(
            f"Il modello '{actor.name}' non ha una parte del rig chiamata '{name}'"
        )


def rigidbody_call(alias: Any = "rigidbody") -> Any:
    """rigidbody.call("RB") — collega un rigidbody e lo espone come player.RB.

    Sta di solito fuori dagli handler, quindi ricade sull'ultimo actor
    dichiarato quando non c'e' nessun handler in esecuzione.
    """
    actor = _engine._current_actor or _engine._declared_actor
    if actor is None:
        raise RuntimeError(
            'rigidbody.call: nessun modello a cui collegarlo (manca "actor nome"?)'
        )
    _validate_component(actor, "rigidbody")
    nome = str(alias)
    rb = RigidBody(actor, nome)
    setattr(actor, nome, rb)
    return rb


def create_cp_module(interpreter: "Interpreter"):
    from cpython.values import NativeFunction, NativeModule

    _track_script_dir(interpreter)

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

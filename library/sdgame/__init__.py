"""sdgame — giochi 2D low-level stile pygame (senza FinityEngine)."""

from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None  # type: ignore


class _State:
    screen = None
    clock = None
    width = 800
    height = 600
    title = "sdgame"
    running = False
    keys_down: set[str] = set()
    keys_pressed = None
    mouse_pos = (0, 0)
    mouse_buttons = (False, False, False)
    bg = (0, 0, 0)
    dt = 0.0  # secondi dall'ultimo tick()


_state = _State()


def _need_pygame() -> None:
    if pygame is None:
        raise RuntimeError("pygame non installato. Esegui: pip install pygame")


def _parse_color(color: Any) -> tuple[int, int, int]:
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return int(color[0]), int(color[1]), int(color[2])
    if isinstance(color, int):
        return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
    if isinstance(color, str):
        s = color.strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        return _parse_color(int(s, 16))
    raise TypeError(f"Colore non valido: {color!r}")


def init(width: Any = 800, height: Any = 600, title: Any = "sdgame", fullscreen: Any = False) -> None:
    """Apre la finestra. sdgame.init(800, 600, "titolo") oppure sdgame.init(fullscreen=true)."""
    _need_pygame()
    pygame.init()
    _state.title = str(title)
    fs = bool(fullscreen) or (
        isinstance(width, str) and str(width).lower() == "fullscreen"
    )
    if fs:
        info = pygame.display.Info()
        _state.width = int(info.current_w)
        _state.height = int(info.current_h)
        _state.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        _state.width = int(width)
        _state.height = int(height)
        _state.screen = pygame.display.set_mode((_state.width, _state.height))
    pygame.display.set_caption(_state.title)
    _state.clock = pygame.time.Clock()
    _state.running = True
    _state.dt = 0.0
    _state.keys_down = set()
    _state.keys_pressed = pygame.key.get_pressed()


def set_title(title: Any) -> None:
    _need_pygame()
    _state.title = str(title)
    pygame.display.set_caption(_state.title)


def fill(color: Any) -> None:
    """Pulisce lo schermo con un colore."""
    assert _state.screen is not None
    _state.screen.fill(_parse_color(color))


def flip() -> None:
    """Mostra il frame disegnato."""
    _need_pygame()
    if _state.screen is not None:
        pygame.display.flip()


def _process_events() -> None:
    """Aggiorna tasti/mouse. Se chiudi la X o Esc → is_running diventa false."""
    if pygame is None or not _state.running:
        return
    _state.keys_down.clear()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            _state.running = False
            return
        if event.type == pygame.KEYDOWN:
            _state.keys_down.add(pygame.key.name(event.key))
            if event.key == pygame.K_ESCAPE:
                _state.running = False
                return
    _state.keys_pressed = pygame.key.get_pressed()
    _state.mouse_pos = pygame.mouse.get_pos()
    _state.mouse_buttons = pygame.mouse.get_pressed()


def tick(fps: Any = 60) -> float:
    """
    Un frame: legge input, limita gli FPS, aggiorna sdgame.dt().
    Se l'utente chiude la finestra, sdgame.is_running() diventa false
    e il while termina da solo (niente poll/break).
    """
    assert _state.clock is not None
    _process_events()
    if not _state.running:
        _state.dt = 0.0
        return 0.0
    _state.dt = _state.clock.tick(int(fps)) / 1000.0
    return _state.dt


def dt() -> float:
    """Delta time dell'ultimo tick(), in secondi."""
    return float(_state.dt)


def quit_() -> None:
    """Chiude definitivamente la finestra e spegne sdgame."""
    _state.running = False
    _state.dt = 0.0
    _state.keys_down = set()
    _state.keys_pressed = None
    _state.mouse_buttons = (False, False, False)
    if pygame is None:
        _state.screen = None
        _state.clock = None
        return
    try:
        if _state.screen is not None:
            pygame.display.quit()
    except Exception:
        pass
    _state.screen = None
    _state.clock = None
    try:
        pygame.quit()
    except Exception:
        pass


def is_running() -> bool:
    return bool(_state.running)


def key(name: Any) -> bool:
    """True se il tasto è premuto in questo frame (tenuto). Preferisci getkey."""
    return getkey(name)


def getkey(name: Any) -> bool:
    """True se il tasto è premuto in questo frame (tenuto)."""
    _need_pygame()
    if _state.keys_pressed is None:
        return False
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
        "enter": pygame.K_RETURN,
        "return": pygame.K_RETURN,
    }
    code = mapping.get(str(name).lower())
    if code is None:
        return False
    return bool(_state.keys_pressed[code])


def key_down(name: Any) -> bool:
    return getkeydown(name)


def getkeydown(name: Any) -> bool:
    """True solo nel frame in cui il tasto è stato premuto."""
    return str(name).lower() in _state.keys_down


def mouse_x() -> int:
    return int(_state.mouse_pos[0])


def mouse_y() -> int:
    return int(_state.mouse_pos[1])


def mouse_button(button: Any = 1) -> bool:
    """1=sinistro, 2=centro, 3=destro."""
    idx = int(button) - 1
    if idx < 0 or idx >= len(_state.mouse_buttons):
        return False
    return bool(_state.mouse_buttons[idx])


def rect(x: Any, y: Any, w: Any, h: Any, color: Any) -> None:
    if _state.screen is None:
        return
    pygame.draw.rect(
        _state.screen,
        _parse_color(color),
        pygame.Rect(int(x), int(y), int(w), int(h)),
    )


def circle(x: Any, y: Any, radius: Any, color: Any) -> None:
    if _state.screen is None:
        return
    pygame.draw.circle(
        _state.screen,
        _parse_color(color),
        (int(x), int(y)),
        int(radius),
    )


def line(x1: Any, y1: Any, x2: Any, y2: Any, color: Any, width: Any = 1) -> None:
    if _state.screen is None:
        return
    pygame.draw.line(
        _state.screen,
        _parse_color(color),
        (int(x1), int(y1)),
        (int(x2), int(y2)),
        int(width),
    )


def text(message: Any, x: Any, y: Any, color: Any = 0xFFFFFF, size: Any = 24) -> None:
    if _state.screen is None:
        return
    font = pygame.font.SysFont(None, int(size))
    surf = font.render(str(message), True, _parse_color(color))
    _state.screen.blit(surf, (int(x), int(y)))


def image(path: Any, x: Any, y: Any, w: Any = None, h: Any = None) -> None:
    if _state.screen is None:
        return
    surf = pygame.image.load(str(path)).convert_alpha()
    if w is not None and h is not None:
        surf = pygame.transform.scale(surf, (int(w), int(h)))
    _state.screen.blit(surf, (int(x), int(y)))


def width() -> int:
    return int(_state.width)


def height() -> int:
    return int(_state.height)


def create_cp_module(interpreter):
    from cpython.values import NativeFunction, NativeModule

    return NativeModule(
        "sdgame",
        {
            "init": NativeFunction("init", init),
            "set_title": NativeFunction("set_title", set_title),
            "fill": NativeFunction("fill", fill),
            "flip": NativeFunction("flip", flip),
            "tick": NativeFunction("tick", tick),
            "dt": NativeFunction("dt", dt),
            "quit": NativeFunction("quit", quit_),
            "is_running": NativeFunction("is_running", is_running),
            "key": NativeFunction("key", key),  # alias legacy
            "getkey": NativeFunction("getkey", getkey),
            "key_down": NativeFunction("key_down", key_down),
            "getkeydown": NativeFunction("getkeydown", getkeydown),
            "mouse_x": NativeFunction("mouse_x", mouse_x),
            "mouse_y": NativeFunction("mouse_y", mouse_y),
            "mouse_button": NativeFunction("mouse_button", mouse_button),
            "rect": NativeFunction("rect", rect),
            "circle": NativeFunction("circle", circle),
            "line": NativeFunction("line", line),
            "text": NativeFunction("text", text),
            "image": NativeFunction("image", image),
            "width": NativeFunction("width", width),
            "height": NativeFunction("height", height),
        },
    )

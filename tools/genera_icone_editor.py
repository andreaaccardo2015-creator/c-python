"""Genera icone editor dal logo ufficiale (preferisce logo.png, poi logo.ico)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parent.parent
media = root / "editors" / "vscode-c-python" / "media"
icons = root / "editors" / "vscode-c-python" / "fileicons"
media.mkdir(parents=True, exist_ok=True)
icons.mkdir(parents=True, exist_ok=True)

ico = root / "logo.ico"
png = root / "logo.png"
src = png if png.is_file() else ico
if not src.is_file():
    raise SystemExit("logo.ico / logo.png non trovati")


def _best_frame(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    if getattr(img, "n_frames", 1) <= 1:
        return img
    best = None
    best_area = 0
    for i in range(img.n_frames):
        img.seek(i)
        frame = img.copy().convert("RGBA")
        area = frame.size[0] * frame.size[1]
        if area > best_area:
            best_area = area
            best = frame
    return best if best is not None else img.convert("RGBA")


def _is_bg(p: tuple[int, int, int, int]) -> bool:
    r, g, b, a = p
    return a < 10 or (r > 245 and g > 245 and b > 245)


def _make_transparent(img: Image.Image) -> Image.Image:
    """Sfondo bianco esterno → trasparente (flood-fill dai bordi)."""
    out = img.convert("RGBA")
    w, h = out.size
    px = out.load()
    seen = [[False] * w for _ in range(h)]
    stack: list[tuple[int, int]] = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x]:
            continue
        seen[y][x] = True
        if not _is_bg(px[x, y]):
            continue
        px[x, y] = (0, 0, 0, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return out


def _content_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    px = img.load()
    w, h = img.size
    minx, miny, maxx, maxy = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            if not _is_bg(px[x, y]):
                found = True
                minx = min(minx, x)
                miny = min(miny, y)
                maxx = max(maxx, x)
                maxy = max(maxy, y)
    if not found:
        return 0, 0, w - 1, h - 1
    return minx, miny, maxx, maxy


def _hexagon_crop(img: Image.Image) -> Image.Image:
    """Solo esagono+C (senza testo 'python') per icone file piccole."""
    px = img.load()
    w, h = img.size
    rows: list[tuple[int, int, int]] = []
    for y in range(h):
        xs = [x for x in range(w) if not _is_bg(px[x, y])]
        if xs:
            rows.append((y, min(xs), max(xs)))
    if not rows:
        return img

    max_w = max(x1 - x0 for _, x0, x1 in rows)
    hex_bottom = rows[0][0]
    for y, x0, x1 in rows:
        if (x1 - x0) > 0.72 * max_w:
            hex_bottom = y

    y_set = {y for y, _, _ in rows}
    for y in range(hex_bottom, rows[-1][0] + 1):
        if y not in y_set and y > hex_bottom + 5:
            hex_bottom = y - 1
            break

    minx = min(x0 for y, x0, x1 in rows if y <= hex_bottom)
    maxx = max(x1 for y, x0, x1 in rows if y <= hex_bottom)
    miny = rows[0][0]
    pad = max(4, (maxx - minx) // 40)
    minx = max(0, minx - pad)
    miny = max(0, miny - pad)
    maxx = min(w - 1, maxx + pad)
    maxy = min(h - 1, hex_bottom + pad)
    return img.crop((minx, miny, maxx + 1, maxy + 1))


def _fit_square(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - img.size[0]) // 2
    y = (size - img.size[1]) // 2
    canvas.paste(img, (x, y), img)
    return canvas


# SVG vettoriale semplice (niente PNG base64 → niente warning SVG in Cursor)
HEX_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <path fill="#3B6FBF" d="M16 2.5L27.5 9.25v13.5L16 29.5 4.5 22.75V9.25L16 2.5z"/>
  <path fill="#2A4F8F" d="M16 2.5L27.5 9.25 16 16 4.5 9.25 16 2.5z" opacity=".85"/>
  <path fill="#1E3A6E" d="M27.5 9.25V22.75L16 29.5V16l11.5-6.75z" opacity=".9"/>
  <path fill="#fff" d="M20.2 10.2c-.7-.9-1.85-1.45-3.25-1.45-2.7 0-4.65 2.1-4.65 5.1s1.95 5.1 4.65 5.1c1.45 0 2.6-.55 3.3-1.5l-1.45-1.05c-.4.5-.95.8-1.75.8-1.5 0-2.55-1.2-2.55-3.35s1.05-3.35 2.55-3.35c.75 0 1.3.25 1.7.7l1.45-1.1z"/>
</svg>
"""

if ico.is_file():
    shutil.copy2(ico, media / "logo.ico")
if png.is_file():
    shutil.copy2(png, media / "logo.png")

full = _make_transparent(_best_frame(Image.open(src)))
bx0, by0, bx1, by1 = _content_bbox(full)
full_crop = full.crop((bx0, by0, bx1 + 1, by1 + 1))
mark = _make_transparent(_hexagon_crop(full))

for size, name in [(16, "cpython-16.png"), (32, "cpython-32.png"), (64, "cpython-64.png"), (128, "cpython-128.png")]:
    out = _fit_square(mark, size)
    out.save(media / name)
    out.save(icons / name)

file_icon = _fit_square(mark, 64)
file_icon.save(icons / "cpython.png")
# SVG puro per language icon / fallback (no data-URI)
(icons / "cpython.svg").write_text(HEX_SVG, encoding="utf-8")
(media / "cpython-lang.svg").write_text(HEX_SVG, encoding="utf-8")
(media / "activity.svg").write_text(HEX_SVG, encoding="utf-8")

_fit_square(full_crop, 128).save(media / "icon.png")

(icons / "file.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<path fill="#90a4ae" d="M6 2h13l7 7v21H6z"/>'
    '<path fill="#cfd8dc" d="M19 2v7h7z"/></svg>\n',
    encoding="utf-8",
)
(icons / "folder.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<path fill="#90caf9" d="M4 8h10l2 2h12v14H4z"/></svg>\n',
    encoding="utf-8",
)
(icons / "folder-open.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<path fill="#64b5f6" d="M4 10h9l2 2h13v12H4z"/>'
    '<path fill="#90caf9" d="M4 8h10l2 2H4z"/></svg>\n',
    encoding="utf-8",
)

if png.is_file():
    ico_img = _make_transparent(_best_frame(Image.open(png)))
    ico_mark = _fit_square(_hexagon_crop(ico_img), 256)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_mark.save(root / "logo.ico", format="ICO", sizes=sizes)
    shutil.copy2(root / "logo.ico", media / "logo.ico")
    local = Path.home() / "AppData" / "Local" / "CPython" / "logo.ico"
    if local.parent.is_dir():
        shutil.copy2(root / "logo.ico", local)

# Non copiare logo.png (1MB+) nelle fileicons — evita bloat/warning
for bulky in ("logo.png", "logo.ico"):
    p = icons / bulky
    if p.is_file():
        p.unlink()

print("ok from", src.name, "png+vector-svg (no data-uri)")

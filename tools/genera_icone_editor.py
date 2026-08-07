from PIL import Image
from pathlib import Path

root = Path(__file__).resolve().parent.parent
media = root / "editors" / "vscode-c-python" / "media"
icons = root / "editors" / "vscode-c-python" / "fileicons"
icons.mkdir(parents=True, exist_ok=True)

img = Image.open(root / "logo.png").convert("RGBA")

for size, name in [(16, "cpython-16.png"), (32, "cpython-32.png"), (64, "cpython-64.png"), (128, "cpython-128.png")]:
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    out.save(media / name)
    out.save(icons / name)

# Icona principale tema file (PNG: VS Code/Cursor la leggono bene)
img.resize((64, 64), Image.Resampling.LANCZOS).save(icons / "cpython.png")
img.resize((128, 128), Image.Resampling.LANCZOS).save(media / "icon.png")

# SVG semplice (linguaggio / tab) — senza data-URI
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#3B6FBF"/>
      <stop offset="100%" stop-color="#1E3A6E"/>
    </linearGradient>
  </defs>
  <path fill="url(#g)" d="M16 2.2l11.5 6.65v13.3L16 28.8 4.5 22.15V8.85L16 2.2z"/>
  <text x="16" y="21" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" font-weight="700" fill="#fff">C</text>
</svg>
"""
(media / "cpython-lang.svg").write_text(svg, encoding="utf-8")
(icons / "cpython.svg").write_text(svg, encoding="utf-8")

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
print("icons ok")

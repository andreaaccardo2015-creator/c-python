"""Genera logo.icns da logo.png (per macOS .app)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Serve Pillow: pip install Pillow")
        return 1

    src = ROOT / "logo.png"
    if not src.is_file():
        print("logo.png non trovato")
        return 1

    img = Image.open(src).convert("RGBA")
    out = ROOT / "logo.icns"
    sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512)]
    try:
        img.save(out, format="ICNS", sizes=sizes)
        print("ok", out, out.stat().st_size)
        return 0
    except Exception as e:
        print("Pillow ICNS fallito:", e)

    iconset = ROOT / "logo.iconset"
    iconset.mkdir(exist_ok=True)
    pairs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for name, size in pairs:
        img.resize((size, size), Image.Resampling.LANCZOS).save(iconset / name)
    print("Creato logo.iconset — su macOS: iconutil -c icns logo.iconset -o logo.icns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

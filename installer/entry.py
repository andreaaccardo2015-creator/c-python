"""Entry point PyInstaller: install / demone / CLI."""

from __future__ import annotations

import sys
from pathlib import Path

# Assicura root bundle / repo su sys.path
if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)
else:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from daemon.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())

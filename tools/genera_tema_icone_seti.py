"""Genera tema icone cpython-seti: Seti completo + logo solo per .cpy/.cp."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "editors" / "vscode-c-python" / "fileicons" / "seti-base"
THEME_OUT = ROOT / "editors" / "vscode-c-python" / "fileicons" / "cpython-seti-icon-theme.json"


def _find_seti() -> Path | None:
    home = Path.home()
    candidates = [
        home / "AppData/Local/Programs/cursor/resources/app/extensions/theme-seti",
        home / "AppData/Local/Programs/Cursor/resources/app/extensions/theme-seti",
        Path(r"C:\Program Files\Cursor\resources\app\extensions\theme-seti"),
        home / "AppData/Local/Programs/Microsoft VS Code/resources/app/extensions/theme-seti",
        Path(r"C:\Program Files\Microsoft VS Code\resources\app\extensions\theme-seti"),
        # macOS
        Path("/Applications/Cursor.app/Contents/Resources/app/extensions/theme-seti"),
        Path("/Applications/Visual Studio Code.app/Contents/Resources/app/extensions/theme-seti"),
        # Linux
        Path("/usr/share/cursor/resources/app/extensions/theme-seti"),
        Path("/usr/share/code/resources/app/extensions/theme-seti"),
    ]
    for c in candidates:
        if (c / "icons" / "vs-seti-icon-theme.json").is_file():
            return c
    return None


def _rebase(path: str) -> str:
    """Riporta un path relativo del tema Seti dentro ./seti-base/.

    Seti usa sia './x.svg' che 'x.svg': entrambe le forme vanno riscritte,
    altrimenti l'asset non viene trovato dal tema che vive in fileicons/.
    """
    if not path or path.startswith(("./seti-base/", "data:", "http")):
        return path
    return "./seti-base/" + path.lstrip("./")


def main() -> int:
    seti = _find_seti()
    if seti is None:
        print("Seti non trovato: tema cpython-seti non generato")
        return 1

    src_icons = seti / "icons"
    OUT.mkdir(parents=True, exist_ok=True)

    # Copia asset Seti necessari
    for name in ("seti.woff", "vs-seti-icon-theme.json", "cursor.svg", "cursor_mini.svg", "cursor_mini_light.svg"):
        s = src_icons / name
        if s.is_file():
            shutil.copy2(s, OUT / name)

    # Logo C Python (solo asset leggeri — no logo.png da 1MB+)
    for name in ("cpython.png", "cpython.svg"):
        s = ROOT / "editors" / "vscode-c-python" / "fileicons" / name
        if s.is_file():
            shutil.copy2(s, OUT / name)

    # Pulisci residui pesanti da installazioni precedenti
    for bulky in ("logo.png", "logo.ico"):
        p = OUT / bulky
        if p.is_file():
            p.unlink()

    theme_src = OUT / "vs-seti-icon-theme.json"
    data = json.loads(theme_src.read_text(encoding="utf-8"))

    defs = data.setdefault("iconDefinitions", {})
    # PNG ufficiale ritagliato (affidabile); SVG vettoriale come fallback
    if (OUT / "cpython.png").is_file():
        logo_icon = "./seti-base/cpython.png"
    else:
        logo_icon = "./seti-base/cpython.svg"
    defs["_cpython_file"] = {"iconPath": logo_icon}

    exts = data.setdefault("fileExtensions", {})
    exts["cpy"] = "_cpython_file"
    exts["cp"] = "_cpython_file"

    langs = data.setdefault("languageIds", {})
    langs["cpython"] = "_cpython_file"

    # Tema finale vive in fileicons/ ma usa asset in seti-base/
    for font in data.get("fonts", []):
        for src in font.get("src", []):
            if "path" in src:
                src["path"] = _rebase(src["path"])

    for val in defs.values():
        if isinstance(val, dict) and "iconPath" in val:
            val["iconPath"] = _rebase(val["iconPath"])

    # Il JSON tema sta in fileicons/cpython-seti-icon-theme.json
    THEME_OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ok", THEME_OUT)
    print("seti from", seti)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

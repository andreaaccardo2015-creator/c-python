"""Helper condivisi associazioni editor (tutte le piattaforme)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def merge_json_settings(path: Path, associations: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    raw = ""
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            try:
                import re

                cleaned = re.sub(r"//.*?$", "", raw, flags=re.M)
                cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S)
                cleaned = re.sub(r",\s*}", "}", cleaned)
                cleaned = re.sub(r",\s*]", "]", cleaned)
                data = json.loads(cleaned)
            except Exception:
                data = {}
    fa = data.get("files.associations")
    if not isinstance(fa, dict):
        fa = {}
    fa.update(associations)
    data["files.associations"] = fa
    # Tema Seti + logo solo per .cpy/.cp (allineato a extension.js)
    if data.get("workbench.iconTheme") in (
        None,
        "",
        "cpython-file-icons",
        "vs-seti",
        "vs-minimal",
    ):
        data["workbench.iconTheme"] = "cpython-seti"
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_editor_associations() -> None:
    assoc = {"*.cpy": "cpython", "*.cp": "cpython"}
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform == "darwin":
        app_support = home / "Library" / "Application Support"
        candidates += [
            app_support / "Code" / "User" / "settings.json",
            app_support / "Cursor" / "User" / "settings.json",
            app_support / "VSCodium" / "User" / "settings.json",
            app_support / "Code - Insiders" / "User" / "settings.json",
        ]
    elif sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", ""))
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates += [
            appdata / "Code" / "User" / "settings.json",
            appdata / "Cursor" / "User" / "settings.json",
            appdata / "VSCodium" / "User" / "settings.json",
            appdata / "Code - Insiders" / "User" / "settings.json",
            local / "Programs" / "Microsoft VS Code" / "data" / "user-data" / "User" / "settings.json",
        ]
    else:
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        candidates += [
            config / "Code" / "User" / "settings.json",
            config / "Cursor" / "User" / "settings.json",
            config / "VSCodium" / "User" / "settings.json",
        ]

    for p in candidates:
        try:
            if p.parent.is_dir():
                merge_json_settings(p, assoc)
        except Exception:
            pass


def install_notepadpp_udl() -> None:
    """Solo Windows — no-op altrove."""
    if sys.platform != "win32":
        return
    appdata = Path(os.environ.get("APPDATA", ""))
    if not (appdata / "Notepad++").is_dir():
        return
    try:
        udl_dir = appdata / "Notepad++" / "userDefineLangs"
        udl_dir.mkdir(parents=True, exist_ok=True)
        # UDL minimale
        (udl_dir / "CPython.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8" ?>\n'
            '<NotepadPlus><UserLang name="C Python" ext="cpy cp" udlVersion="2.1">'
            "<Settings><Global caseIgnored=\"yes\" /></Settings></UserLang></NotepadPlus>\n",
            encoding="utf-8",
        )
    except Exception:
        pass

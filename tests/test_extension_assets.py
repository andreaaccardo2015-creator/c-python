"""Verifica che l'estensione editor non riferisca asset inesistenti."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "editors" / "vscode-c-python"


class TestExtensionAssets(unittest.TestCase):
    def test_json_files_are_valid(self):
        for p in sorted(EXT.rglob("*.json")):
            with self.subTest(file=p.relative_to(ROOT)):
                json.loads(p.read_text(encoding="utf-8"))

    def test_manifest_paths_exist(self):
        pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
        self.assertTrue((EXT / pkg["main"]).is_file(), pkg["main"])
        contributes = pkg.get("contributes", {})
        for grammar in contributes.get("grammars", []):
            self.assertTrue((EXT / grammar["path"]).is_file(), grammar["path"])
        for theme in contributes.get("iconThemes", []):
            self.assertTrue((EXT / theme["path"]).is_file(), theme["path"])
        for lang in contributes.get("languages", []):
            icon = lang.get("icon")
            if isinstance(icon, dict):
                for variant in icon.values():
                    self.assertTrue((EXT / variant).is_file(), variant)

    def test_icon_themes_have_no_dangling_assets(self):
        """Regressione: gli iconPath Seti senza './' restavano fuori da seti-base/."""
        pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
        themes = pkg.get("contributes", {}).get("iconThemes", [])
        self.assertTrue(themes, "nessun tema icone dichiarato")
        for theme in themes:
            theme_path = EXT / theme["path"]
            data = json.loads(theme_path.read_text(encoding="utf-8"))
            base = theme_path.parent
            for name, definition in data.get("iconDefinitions", {}).items():
                icon_path = definition.get("iconPath") if isinstance(definition, dict) else None
                if icon_path:
                    with self.subTest(theme=theme["id"], icon=name):
                        self.assertTrue((base / icon_path).is_file(), icon_path)
            for font in data.get("fonts", []):
                for src in font.get("src", []):
                    path = src.get("path")
                    if path:
                        with self.subTest(theme=theme["id"], font=path):
                            self.assertTrue((base / path).is_file(), path)

    def test_cpy_extension_mapped_in_themes(self):
        for theme in json.loads((EXT / "package.json").read_text(encoding="utf-8"))[
            "contributes"
        ]["iconThemes"]:
            data = json.loads((EXT / theme["path"]).read_text(encoding="utf-8"))
            exts = data.get("fileExtensions", {})
            for suffix in ("cpy", "cp"):
                with self.subTest(theme=theme["id"], ext=suffix):
                    self.assertIn(suffix, exts)


if __name__ == "__main__":
    unittest.main()

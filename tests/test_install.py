"""Test del rilevamento versione installata."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cpython import __version__
from daemon import install


class TestInstalledVersion(unittest.TestCase):
    def test_current_version_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / install.MARKER).write_text(__version__, encoding="utf-8")
            with patch.object(install, "install_root", return_value=root):
                self.assertTrue(install.is_installed())

    def test_legacy_ok_marker_forces_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / install.MARKER).write_text("ok", encoding="utf-8")
            with patch.object(install, "install_root", return_value=root):
                self.assertFalse(install.is_installed())

    def test_old_version_forces_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / install.MARKER).write_text("0.2.0", encoding="utf-8")
            with patch.object(install, "install_root", return_value=root):
                self.assertFalse(install.is_installed())

    def test_missing_marker_is_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(install, "install_root", return_value=Path(tmp)):
                self.assertFalse(install.is_installed())


if __name__ == "__main__":
    unittest.main()

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


class TestMacDmgInstall(unittest.TestCase):
    def test_bundle_path_is_detected(self):
        from daemon.paths import mac_app_bundle_from_exe

        exe = Path("/Volumes/C Python/Cpython_interpreter_macos.app/Contents/MacOS/Cpython_interpreter")
        bundle = mac_app_bundle_from_exe(exe)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.name, "Cpython_interpreter_macos.app")

    def test_volumes_path_is_a_dmg(self):
        from daemon.paths import is_running_from_dmg

        exe = Path("/Volumes/C Python/Cpython_interpreter_macos.app/Contents/MacOS/Cpython_interpreter")
        self.assertTrue(is_running_from_dmg(exe))

    def test_applications_path_is_not_a_dmg(self):
        from daemon.paths import is_running_from_dmg

        exe = Path("/Applications/Cpython_interpreter_macos.app/Contents/MacOS/Cpython_interpreter")
        self.assertFalse(is_running_from_dmg(exe))

    def test_maybe_install_from_dmg_is_noop_off_mac(self):
        self.assertIsNone(install.maybe_install_from_dmg([]))

    def test_copy_skips_when_already_at_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "Cpython_interpreter_macos.app"
            (src / "Contents" / "MacOS").mkdir(parents=True)
            (src / "Contents" / "MacOS" / "Cpython_interpreter").write_text("x", encoding="utf-8")
            dests = [src]
            with patch.object(install, "mac_app_install_destinations", return_value=dests):
                with patch.object(install, "mac_app_bundle_from_exe", return_value=src):
                    out = install.install_app_to_applications(src / "Contents" / "MacOS" / "Cpython_interpreter")
            self.assertEqual(out, src)
            self.assertTrue((src / "Contents" / "MacOS" / "Cpython_interpreter").is_file())


if __name__ == "__main__":
    unittest.main()

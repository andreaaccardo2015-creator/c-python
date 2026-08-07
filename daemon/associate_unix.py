"""Fallback Linux / altri: solo associazioni editor."""

from __future__ import annotations

from pathlib import Path

from .associate_common import patch_editor_associations
from .paths import install_root


def register_file_association(open_command: str | None = None) -> None:
    install_root().mkdir(parents=True, exist_ok=True)
    patch_editor_associations()
    # Desktop entry opzionale
    try:
        apps = Path.home() / ".local" / "share" / "applications"
        apps.mkdir(parents=True, exist_ok=True)
        desktop = apps / "cpython.desktop"
        exe = install_root() / "Cpython_interpreter"
        desktop.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=C Python\n"
            "Comment=C Python Interpreter\n"
            f"Exec={exe} --open %f\n"
            "MimeType=text/x-cpython;\n"
            "Categories=Development;\n",
            encoding="utf-8",
        )
        mime = Path.home() / ".local" / "share" / "mime" / "packages"
        mime.mkdir(parents=True, exist_ok=True)
        (mime / "cpython.xml").write_text(
            '<?xml version="1.0"?>\n'
            '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
            '  <mime-type type="text/x-cpython">\n'
            "    <comment>C Python source</comment>\n"
            '    <glob pattern="*.cpy"/>\n'
            '    <glob pattern="*.cp"/>\n'
            "  </mime-type>\n"
            "</mime-info>\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def register_startup(exe_path: Path) -> None:
    autostart = Path.home() / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    (autostart / "cpython-interpreter.desktop").write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=C Python Interpreter\n"
        f"Exec={exe_path} --daemon\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


def unregister_startup() -> None:
    p = Path.home() / ".config" / "autostart" / "cpython-interpreter.desktop"
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def notify_shell_change() -> None:
    pass

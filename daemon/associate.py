"""Associazione file .cpy / .cp — dispatcher per piattaforma."""

from __future__ import annotations

import sys
from pathlib import Path


def register_file_association(open_command: str | None = None) -> None:
    if sys.platform == "win32":
        from .associate_win import register_file_association as impl
    elif sys.platform == "darwin":
        from .associate_mac import register_file_association as impl
    else:
        from .associate_unix import register_file_association as impl
    impl(open_command=open_command)


def register_startup(exe_path: Path) -> None:
    if sys.platform == "win32":
        from .associate_win import register_startup as impl
    elif sys.platform == "darwin":
        from .associate_mac import register_startup as impl
    else:
        from .associate_unix import register_startup as impl
    impl(exe_path)


def unregister_startup() -> None:
    if sys.platform == "win32":
        from .associate_win import unregister_startup as impl
    elif sys.platform == "darwin":
        from .associate_mac import unregister_startup as impl
    else:
        from .associate_unix import unregister_startup as impl
    impl()


def notify_shell_change() -> None:
    if sys.platform == "win32":
        from .associate_win import notify_shell_change as impl
    elif sys.platform == "darwin":
        from .associate_mac import notify_shell_change as impl
    else:
        from .associate_unix import notify_shell_change as impl
    impl()

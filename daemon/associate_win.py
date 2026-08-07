"""Associazione Windows globale .cpy / .cp + logo."""

from __future__ import annotations

import json
import os
import sys
import winreg
from pathlib import Path

from .paths import install_root, logo_ico

PROG_ID = "CPython.Document"
EXTENSIONS = (".cpy", ".cp")
FRIENDLY_TYPE = "C Python Source File"


def _set_reg(key_path: str, name: str | None, value: str, root=winreg.HKEY_CURRENT_USER) -> None:
    key = winreg.CreateKeyEx(root, key_path, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def _delete_tree(key_path: str, root=winreg.HKEY_CURRENT_USER) -> None:
    try:
        key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        return
    try:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(f"{key_path}\\{sub}", root)
        winreg.CloseKey(key)
        winreg.DeleteKey(root, key_path)
    except OSError:
        try:
            winreg.CloseKey(key)
        except Exception:
            pass


def register_file_association(open_command: str | None = None) -> None:
    ico_path = logo_ico()
    ico = str(ico_path.resolve()) if ico_path.is_file() else str(ico_path)
    root = install_root()

    if open_command is None:
        open_cmd_exe = root / "Cpython_interpreter_64x_win.exe"
        if open_cmd_exe.is_file():
            open_command = f'"{open_cmd_exe}" --open "%1"'
        else:
            open_command = (
                'cmd /c (where code >nul 2>&1 && code "%1") || '
                '(where cursor >nul 2>&1 && cursor "%1") || notepad.exe "%1"'
            )

    _set_reg(rf"Software\Classes\{PROG_ID}", None, FRIENDLY_TYPE)
    _set_reg(rf"Software\Classes\{PROG_ID}", "FriendlyTypeName", FRIENDLY_TYPE)
    _set_reg(rf"Software\Classes\{PROG_ID}\DefaultIcon", None, f"{ico},0")
    _set_reg(rf"Software\Classes\{PROG_ID}\shell\open\command", None, open_command)
    _set_reg(rf"Software\Classes\{PROG_ID}\shell\run", None, "Esegui con C Python")
    run_cmd = f'"{root / "bin" / "cpy.bat"}" run "%1"'
    _set_reg(rf"Software\Classes\{PROG_ID}\shell\run\command", None, run_cmd)

    for ext in EXTENSIONS:
        _set_reg(rf"Software\Classes\{ext}", None, PROG_ID)
        _set_reg(rf"Software\Classes\{ext}", "Content Type", "text/x-cpython")
        _set_reg(rf"Software\Classes\{ext}", "PerceivedType", "text")
        _set_reg(rf"Software\Classes\{ext}\OpenWithProgids", PROG_ID, "")
        _set_reg(
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithProgids",
            PROG_ID,
            "",
        )
        _delete_tree(
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice"
        )

    _set_reg(r"Software\CPython\Capabilities", "ApplicationName", "C Python")
    _set_reg(r"Software\CPython\Capabilities", "ApplicationDescription", "Linguaggio C Python")
    _set_reg(r"Software\CPython\Capabilities\FileAssociations", ".cpy", PROG_ID)
    _set_reg(r"Software\CPython\Capabilities\FileAssociations", ".cp", PROG_ID)
    _set_reg(r"Software\RegisteredApplications", "CPython", r"Software\CPython\Capabilities")

    from .associate_common import patch_editor_associations, install_notepadpp_udl

    patch_editor_associations()
    install_notepadpp_udl()


def register_startup(exe_path: Path) -> None:
    key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        winreg.SetValueEx(key, "CPythonInterpreter", 0, winreg.REG_SZ, f'"{exe_path}" --daemon')
    finally:
        winreg.CloseKey(key)


def unregister_startup() -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "CPythonInterpreter")
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
    except OSError:
        pass


def notify_shell_change() -> None:
    try:
        import ctypes

        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass

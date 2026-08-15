"""Installazione locale cross-platform: file, PATH, startup, editor, demone."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from cpython import __version__

from .associate import notify_shell_change, register_file_association, register_startup, unregister_startup
from .paths import (
    MAC_APP_BUNDLE,
    MAC_APP_INNER,
    app_executable,
    bundle_root,
    ensure_install_dirs,
    install_root,
    is_frozen,
    is_running_from_dmg,
    mac_app_bundle_from_exe,
    mac_app_install_destinations,
)
from .tray import is_daemon_alive, start_daemon_detached

MARKER = "installed.flag"


def is_installed() -> bool:
    """True solo se è installata esattamente la versione corrente.

    I vecchi setup scrivevano semplicemente ``ok``: sono considerati obsoleti,
    così un nuovo EXE aggiorna automaticamente runtime ed estensione editor.
    """
    marker = install_root() / MARKER
    try:
        return marker.read_text(encoding="utf-8").strip() == __version__
    except OSError:
        return False


def maybe_install_from_dmg(argv: list[str] | None = None) -> int | None:
    """Se l'app e' lanciata dal .dmg, copiala in Applicazioni e rilanciala.

    Ritorna un exit code se QUESTO processo deve uscire (ha gia' avviato
    la copia in Applicazioni). Ritorna None se si continua qui.
    """
    if sys.platform != "darwin" or not is_frozen():
        return None
    args = list(argv or [])
    if "--from-dmg-install" in args:
        return None
    if not is_running_from_dmg():
        return None

    dest = install_app_to_applications()
    if dest is None:
        return None

    rest = [a for a in args if a != "--from-dmg-install"]
    try:
        subprocess.Popen(["open", "-n", str(dest), "--args", "--from-dmg-install", *rest])
    except Exception:
        return None

    _notify_mac_installed(dest)
    _eject_own_dmg()
    return 0


def install_app_to_applications(exe: Path | None = None) -> Path | None:
    """Copia il .app dal disco del DMG in Applicazioni. Ritorna il bundle copiato."""
    exe = Path(exe or sys.executable).resolve()
    src = mac_app_bundle_from_exe(exe)
    if src is None or not src.is_dir():
        return None

    last_error: Exception | None = None
    src_resolved = src.resolve()
    for dest in mac_app_install_destinations():
        try:
            if dest.exists() and dest.resolve() == src_resolved:
                _clear_mac_quarantine(dest)
                return dest
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            _copy_app_bundle(src, dest)
            _clear_mac_quarantine(dest)
            return dest
        except Exception as e:
            last_error = e
            continue
    if last_error:
        print(f"C Python: impossibile copiare in Applicazioni ({last_error})", file=sys.stderr)
    return None


def _copy_app_bundle(src: Path, dest: Path) -> None:
    ditto = shutil.which("ditto")
    if ditto:
        subprocess.run([ditto, str(src), str(dest)], check=True)
        return
    shutil.copytree(src, dest, dirs_exist_ok=True)


def _clear_mac_quarantine(path: Path) -> None:
    try:
        subprocess.run(["xattr", "-cr", str(path)], check=False, capture_output=True)
    except Exception:
        pass


def _notify_mac_installed(dest: Path) -> None:
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'display notification "C Python e\' in Applicazioni e pronto all\'uso." '
                f'with title "C Python" subtitle "{dest.name}"',
            ],
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def _eject_own_dmg() -> None:
    bundle = mac_app_bundle_from_exe()
    if bundle is None:
        return
    volume = bundle.parent
    if "Volumes" not in volume.parts:
        return
    try:
        subprocess.Popen(
            ["hdiutil", "detach", str(volume), "-quiet", "-force"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def do_install() -> int:
    root = ensure_install_dirs()
    src = bundle_root()

    for name in ("logo.ico", "logo.png", "logo.icns"):
        s = src / name
        if s.is_file():
            shutil.copy2(s, root / name)

    for pkg in ("cpython", "daemon", "cpy", "library", "editors"):
        s = src / pkg
        d = root / pkg
        if s.is_dir():
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d, dirs_exist_ok=True)

    # LLVM native lib se presente
    for libname in ("cpython_llvm.dll", "libcpython_llvm.dylib", "libcpython_llvm.so", "cpython_llvm.dylib"):
        dll = src / "llvm_backend" / "build" / libname
        if dll.is_file():
            (root / "llvm_backend" / "build").mkdir(parents=True, exist_ok=True)
            shutil.copy2(dll, root / "llvm_backend" / "build" / libname)

    bin_dir = root / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_cpy_launcher(bin_dir, root)
    _add_to_user_path(str(bin_dir))

    target_exe: Path | None = None
    open_cmd: str | None = None

    if is_frozen():
        exe = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            target_exe = _install_mac_app(exe, root)
            open_cmd = None  # gestito da Info.plist del .app
        elif sys.platform == "win32":
            target_exe = root / "Cpython_interpreter_64x_win.exe"
            try:
                if exe.resolve() != target_exe.resolve():
                    shutil.copy2(exe, target_exe)
            except Exception:
                target_exe = exe
            open_cmd = f'"{target_exe}" --open "%1"'
        else:
            target_exe = root / "Cpython_interpreter"
            try:
                shutil.copy2(exe, target_exe)
                target_exe.chmod(0o755)
            except Exception:
                target_exe = exe
            open_cmd = f'"{target_exe}" --open %f'

        if target_exe:
            register_startup(target_exe)
    else:
        # Dev mode
        py = sys.executable
        repo = str(src.resolve())
        if sys.platform == "win32":
            import winreg

            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                cmd = (
                    f'"{py}" -c "import os,sys; os.chdir(r\'{repo}\'); '
                    f"sys.path.insert(0,r\'{repo}\'); from daemon.__main__ import main; "
                    f"raise SystemExit(main([\'--daemon\']))\""
                )
                winreg.SetValueEx(key, "CPythonInterpreter", 0, winreg.REG_SZ, cmd)
            finally:
                winreg.CloseKey(key)
            open_cmd = 'cmd /c (where code >nul 2>&1 && code "%1") || notepad.exe "%1"'
        else:
            # LaunchAgent / autostart con python -m daemon
            helper = root / "bin" / "cpython-daemon-dev"
            helper.write_text(
                "#!/bin/sh\n"
                f'cd "{repo}"\n'
                f'export PYTHONPATH="{repo}:$PYTHONPATH"\n'
                f'exec "{py}" -m daemon --daemon\n',
                encoding="utf-8",
            )
            helper.chmod(0o755)
            register_startup(helper)

    register_file_association(open_command=open_cmd)
    notify_shell_change()
    _install_editor_extension(src, root)

    tools_src = src / "tools"
    if tools_src.is_dir():
        tools_dst = root / "tools"
        if tools_dst.exists():
            shutil.rmtree(tools_dst, ignore_errors=True)
        shutil.copytree(tools_src, tools_dst, dirs_exist_ok=True)

    (root / MARKER).write_text(__version__, encoding="utf-8")

    if not is_daemon_alive():
        if is_frozen() and target_exe:
            start_daemon_detached(target_exe)
        else:
            start_daemon_detached(None)

    _notify_installed(root)
    return 0


def _write_cpy_launcher(bin_dir: Path, root: Path) -> None:
    if sys.platform == "win32":
        # Ricostruisce gli argomenti con virgolette: evita che path con spazi
        # (es. "c python") si spezzino quando si chiama l'EXE / python.
        (bin_dir / "cpy.bat").write_text(
            f"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "CPYTHON_HOME={root}"
set "PYTHONPATH={root};%PYTHONPATH%"
set "ARGS="
:cpy_args
if "%~1"=="" goto cpy_run
set ARGS=!ARGS! "%~1"
shift
goto cpy_args
:cpy_run
REM Preferisci python -m cpy (sorgenti aggiornati in CPYTHON_HOME).
REM L'EXE frozen puo' contenere una CLI piu' vecchia.
where python >nul 2>&1
if errorlevel 1 goto try_exe
python -m cpy !ARGS!
set "ERR=!ERRORLEVEL!"
endlocal & exit /b %ERR%
:try_exe
if exist "%CPYTHON_HOME%\\Cpython_interpreter_64x_win.exe" (
  "%CPYTHON_HOME%\\Cpython_interpreter_64x_win.exe" --cli !ARGS!
  set "ERR=!ERRORLEVEL!"
  endlocal & exit /b %ERR%
)
echo cpy: Python non trovato e EXE assente.
endlocal & exit /b 1
""",
            encoding="utf-8",
        )
        return

    # macOS / Linux
    app_bin = app_executable()
    script = bin_dir / "cpy"
    script.write_text(
        "#!/bin/sh\n"
        f'export CPYTHON_HOME="{root}"\n'
        f'export PYTHONPATH="{root}:${{PYTHONPATH}}"\n'
        f'APP="{app_bin}"\n'
        'if [ -x "$APP" ]; then\n'
        '  exec "$APP" --cli "$@"\n'
        "else\n"
        '  exec python3 -m cpy "$@"\n'
        "fi\n",
        encoding="utf-8",
    )
    script.chmod(0o755)

    # Symlink comodo su macOS
    if sys.platform == "darwin":
        for link_dir in (Path.home() / "bin", Path("/usr/local/bin")):
            try:
                link_dir.mkdir(parents=True, exist_ok=True)
                link = link_dir / "cpy"
                if link.is_symlink() or link.is_file():
                    link.unlink()
                link.symlink_to(script)
                break
            except Exception:
                continue


def _install_mac_app(exe: Path, root: Path) -> Path:
    """Copia il .app in Applicazioni (e una copia in Application Support)."""
    if "Contents/MacOS" in str(exe):
        app_bundle = exe.parent.parent.parent  # .../Something.app
    else:
        app_bundle = exe.parent / MAC_APP_BUNDLE
        if not app_bundle.is_dir():
            dest_bin = root / MAC_APP_INNER
            try:
                shutil.copy2(exe, dest_bin)
                dest_bin.chmod(0o755)
            except Exception:
                dest_bin = exe
            return dest_bin

    dest = None
    if app_bundle.is_dir():
        try:
            here = app_bundle.resolve()
            for candidate in mac_app_install_destinations():
                if candidate.exists() and candidate.resolve() == here:
                    dest = candidate
                    break
        except Exception:
            dest = None
    if dest is None:
        dest = install_app_to_applications(exe)
    if dest is None:
        dest = app_bundle

    dest2 = root / MAC_APP_BUNDLE
    try:
        if dest2.exists() and dest2.resolve() != dest.resolve():
            shutil.rmtree(dest2, ignore_errors=True)
            shutil.copytree(dest, dest2, dirs_exist_ok=True)
    except Exception:
        pass

    mac_exe = dest / "Contents" / "MacOS" / MAC_APP_INNER
    if not mac_exe.is_file():
        macos_dir = dest / "Contents" / "MacOS"
        if macos_dir.is_dir():
            bins = list(macos_dir.iterdir())
            if bins:
                return bins[0]
    return mac_exe if mac_exe.is_file() else exe


def _install_editor_extension(src: Path, root: Path) -> None:
    home = str(src if (src / "editors").is_dir() else root)
    try:
        if sys.platform == "win32":
            ext_script = src / "tools" / "installa_estensione_vscode.ps1"
            if ext_script.is_file():
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ext_script),
                        "-CPythonHome",
                        home,
                    ],
                    check=False,
                    capture_output=True,
                )
        else:
            sh = src / "tools" / "installa_estensione_vscode.sh"
            if sh.is_file():
                subprocess.run(["bash", str(sh), home], check=False, capture_output=True)
            else:
                # fallback inline
                _copy_vscode_ext(Path(home))
    except Exception:
        pass


def _copy_vscode_ext(cpython_home: Path) -> None:
    ext_src = cpython_home / "editors" / "vscode-c-python"
    if not (ext_src / "package.json").is_file():
        return
    for base in (
        Path.home() / ".vscode" / "extensions",
        Path.home() / ".cursor" / "extensions",
    ):
        try:
            base.mkdir(parents=True, exist_ok=True)
            dest = base / "cpython.c-python-0.2.10"
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(ext_src, dest)
        except Exception:
            pass


def _notify_installed(root: Path) -> None:
    msg = (
        "C Python installato!\n\n"
        "- Demone attivo in background\n"
        "- File .cpy / .cp associati\n"
        "- Comando disponibile: cpy\n\n"
        "Apri un NUOVO terminale e prova:\n"
        "  cpy version\n"
        "  cpy run tuoFile.cpy\n\n"
        f"Cartella: {root}"
    )
    if os.environ.get("CPYTHON_SILENT"):
        print(f"Installato in {root}")
        return
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, msg, "C Python Interpreter", 0x40)
            return
        except Exception:
            pass
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e", f'display notification "C Python pronto" with title "C Python"'],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass
    print(msg)


def do_uninstall() -> int:
    unregister_startup()
    root = install_root()
    try:
        (root / MARKER).unlink(missing_ok=True)
    except Exception:
        pass
    print("Startup rimosso. Puoi cancellare manualmente:", root)
    return 0


def _add_to_user_path(new_dir: str) -> None:
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
        )
        try:
            try:
                current, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current = ""
            parts = [p for p in current.split(";") if p]
            if new_dir not in parts:
                parts.append(new_dir)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
                try:
                    import ctypes

                    ctypes.windll.user32.SendMessageTimeoutW(
                        0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
                    )
                except Exception:
                    pass
        finally:
            winreg.CloseKey(key)
        return

    # macOS / Linux: aggiungi a ~/.zprofile e ~/.bashrc
    line = f'export PATH="{new_dir}:$PATH"  # CPython'
    for rc in (Path.home() / ".zprofile", Path.home() / ".bashrc", Path.home() / ".profile"):
        try:
            existing = rc.read_text(encoding="utf-8") if rc.is_file() else ""
            if "CPython" in existing or new_dir in existing:
                continue
            with rc.open("a", encoding="utf-8") as f:
                f.write("\n" + line + "\n")
        except Exception:
            pass

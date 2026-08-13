from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import CPythonError
from .interpreter import Interpreter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpython", description="Interprete C Python (+ JIT ibrido LLVM)")
    parser.add_argument("file", nargs="?", help="File .cpy (o .cp) da eseguire")
    parser.add_argument("-c", "--code", help="Esegue codice C Python inline")
    parser.add_argument("-v", "--version", action="store_true", help="Mostra versione")
    parser.add_argument(
        "--jit",
        dest="jit",
        action="store_true",
        help="Abilita JIT per funzioni pure (default)",
    )
    parser.add_argument(
        "--no-jit",
        dest="jit",
        action="store_false",
        help="Disabilita il backend JIT C++/LLVM",
    )
    parser.add_argument(
        "--ipc-stdio",
        action="store_true",
        help="Modo editor: handshake ready/bindings con FinityEngine via stdio",
    )
    parser.set_defaults(jit=True)
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__

        root = Path(__file__).resolve().parent.parent
        logo = root / "logo.png"
        print(f"C Python {__version__}")
        if logo.is_file():
            print(f"Logo: {logo}")
        from .llvm_bridge import get_engine, jit_available, jit_load_error

        if jit_available():
            eng = get_engine()
            mode = "LLVM ORC" if eng and eng.is_llvm else "stub C++"
            print(f"JIT: disponibile ({mode})")
        else:
            print(f"JIT: non disponibile ({jit_load_error()})")
        return 0

    enable_jit = bool(args.jit)

    if args.code is not None:
        interp = Interpreter(filename="<string>", enable_jit=enable_jit)
        try:
            interp.run_source(args.code)
            return 0
        except CPythonError as e:
            print(f"Errore: {e}", file=sys.stderr)
            return 1

    if not args.file:
        parser.print_help()
        return 1

    path = Path(args.file)
    if not path.is_file():
        print(f"File non trovato: {path}", file=sys.stderr)
        return 1
    if path.suffix.lower() not in (".cpy", ".cp", ".txt"):
        print(
            f"Avviso: estensione consigliata .cpy (ricevuto {path.suffix or '(nessuna)'})",
            file=sys.stderr,
        )

    source = path.read_text(encoding="utf-8")
    interp = Interpreter(filename=str(path.resolve()), enable_jit=enable_jit)

    if args.ipc_stdio:
        return _run_ipc_stdio(interp, source, str(path))

    try:
        interp.run_source(source)
        return 0
    except CPythonError as e:
        print(f"Errore: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrotto.", file=sys.stderr)
        return 130


def _run_ipc_stdio(interp: Interpreter, source: str, filename: str) -> int:
    """Handshake ready/bindings, poi esecuzione normale con la convalida attiva."""
    from . import __version__, ipc
    from .parser import Parser

    try:
        program = Parser.parse_source(source)
    except CPythonError as e:
        ipc.send_error(e.message, file=filename, line=e.line, column=e.column)
        print(f"Errore: {e}", file=sys.stderr)
        return 1

    actors = ipc.collect_actor_names(program)
    ipc.send_ready(actors, language_version=__version__)
    bindings = ipc.read_bindings(timeout=5.0)

    try:
        import finityengine

        finityengine.set_bindings(bindings)
    except Exception:
        pass  # pygame assente o altro problema di importazione: si prosegue senza convalida

    try:
        interp.exec_program(program)
        return 0
    except CPythonError as e:
        ipc.send_error(e.message, file=filename, line=e.line, column=e.column)
        print(f"Errore: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrotto.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

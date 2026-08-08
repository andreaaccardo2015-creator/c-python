#!/usr/bin/env bash
# Installa estensione C Python in VS Code / Cursor (macOS/Linux)
set -euo pipefail
CPYTHON_HOME="${1:-}"
if [[ -z "$CPYTHON_HOME" ]]; then
  echo "Uso: $0 /path/to/CPythonHome"
  exit 1
fi
EXT_SRC="$CPYTHON_HOME/editors/vscode-c-python"
if [[ ! -f "$EXT_SRC/package.json" ]]; then
  echo "Estensione non trovata: $EXT_SRC"
  exit 1
fi

install_one() {
  local root="$1"
  mkdir -p "$root"
  local dest="$root/cpython.c-python-0.2.10"
  rm -rf "$dest" "$root/cpython.c-python-0.2.9" "$root/cpython.c-python-0.2.8" "$root/cpython.c-python-0.2.7" "$root/cpython.c-python-0.2.6" "$root/cpython.c-python-0.2.5" "$root/cpython.c-python-0.2.4" "$root/cpython.c-python-0.2.3" "$root/cpython.c-python-0.2.2" "$root/cpython.c-python-0.2.1" "$root/cpython.c-python-0.2.0" 2>/dev/null || true
  mkdir -p "$dest"
  cp -R "$EXT_SRC/." "$dest/"
  if [[ -f "$CPYTHON_HOME/logo.png" ]]; then
    mkdir -p "$dest/media"
    cp -f "$CPYTHON_HOME/logo.png" "$dest/media/logo.png"
  fi
  echo "Installata in: $dest"
}

install_one "$HOME/.vscode/extensions"
install_one "$HOME/.cursor/extensions"

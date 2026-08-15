#!/usr/bin/env bash
# Build Cpython_interpreter.app su macOS
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[CPython] Dipendenze..."
python3 -m pip install -q -r requirements-daemon.txt pygame

echo "[CPython] Icona .icns..."
python3 tools/genera_logo_icns.py || true
if [[ ! -f logo.icns && -d logo.iconset ]]; then
  iconutil -c icns logo.iconset -o logo.icns || true
fi

echo "[CPython] PyInstaller .app..."
python3 -m PyInstaller --noconfirm --clean installer/Cpython_interpreter_macos.spec

APP="dist/Cpython_interpreter.app"
if [[ -d "$APP" ]]; then
  echo "OK: $APP"
  # DMG opzionale
    if command -v hdiutil >/dev/null 2>&1; then
    DMG="dist/Cpython_interpreter_64x_win.dmg"
    rm -f "$DMG" dist/Cpython_interpreter_macos.dmg
    hdiutil create -volname "C Python" -srcfolder "$APP" -ov -format UDZO "$DMG"
    echo "OK: $DMG"
  fi
  echo ""
  echo "Installa: trascina $APP in /Applications (o apri doppio click)."
  echo "Poi: open -a Cpython_interpreter  oppure  cpy run file.cpy"
else
  echo "Build fallita: .app non trovato"
  exit 1
fi

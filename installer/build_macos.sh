#!/usr/bin/env bash
# Build Cpython_interpreter_macos.app + Cpython_interpreter_macos.dmg
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

APP="dist/Cpython_interpreter_macos.app"
if [[ ! -d "$APP" && -d dist/Cpython_interpreter.app ]]; then
  mv dist/Cpython_interpreter.app "$APP"
fi

if [[ -d "$APP" ]]; then
  echo "OK: $APP"
  if command -v hdiutil >/dev/null 2>&1; then
    STAGE="$(mktemp -d)"
    cp -R "$APP" "$STAGE/Cpython_interpreter_macos.app"
    # scorciatoia verso Applicazioni, se qualcuno preferisce trascinare
    ln -s /Applications "$STAGE/Applications"
    DMG="dist/Cpython_interpreter_macos.dmg"
    rm -f "$DMG" dist/Cpython_interpreter_64x_win.dmg
    hdiutil create -volname "C Python" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
    rm -rf "$STAGE"
    echo "OK: $DMG"
  fi
  echo ""
  echo "Su Mac: apri $DMG, doppio click su Cpython_interpreter_macos.app."
  echo "L'app si copia da sola in Applicazioni, attiva demone e cpy, e stacca il disco."
else
  echo "Build fallita: .app non trovato"
  exit 1
fi

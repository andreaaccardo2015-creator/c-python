# macOS — Cpython_interpreter_macos.dmg

Da **Windows non si puo' produrre un `.app` nativo**.
Il build macOS avviene su un Mac oppure su **GitHub Actions** (`macos-latest`).

## Cosa fa l'utente

1. Scarica `Cpython_interpreter_macos.dmg`
2. Doppio click sul `.dmg` (si monta il disco)
3. Doppio click su `Cpython_interpreter_macos.app` **una volta**
4. L'app si copia da sola in **Applicazioni**, avvia demone + `cpy`, e stacca il disco

Se Gatekeeper blocca al primo click: **Impostazioni → Privacy e sicurezza → Apri comunque**, poi ritenta.

## Opzione A — GitHub Actions

1. Push di questo progetto
2. Workflow `Build C Python`
3. Artifact `Cpython_interpreter_macos_dmg`

## Opzione B — Build su un Mac locale

```bash
cd "c python"
bash installer/build_macos.sh
open dist/Cpython_interpreter_macos.dmg
```

## Dopo l'install

```bash
cpy version
cpy run tuoFile.cpy
open -a Cpython_interpreter_macos
```

- App: `/Applications/Cpython_interpreter_macos.app` (oppure `~/Applications`)
- Demone: LaunchAgent `com.cpython.interpreter`
- Dati: `~/Library/Application Support/CPython`

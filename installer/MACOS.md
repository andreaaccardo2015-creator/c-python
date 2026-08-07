# macOS build — Cpython_interpreter.app

Da **Windows non si puo' produrre un `.app` nativo**.
Il build macOS avviene su un Mac oppure su **GitHub Actions** (`macos-latest`).

## Opzione A — GitHub Actions (consigliata)

1. Crea un repo GitHub e fai push di questo progetto
2. In Actions parte il workflow `Build C Python`
3. Scarica l'artifact `Cpython_interpreter_macos_app` (`.app` + `.dmg`)
4. Su Mac: apri il `.dmg` o estrai lo zip, trascina `Cpython_interpreter.app` in **Applicazioni**
5. Al primo avvio installa demone + `cpy` + associazioni `.cpy`

## Opzione B — Build su un Mac locale

```bash
cd "c python"
bash installer/build_macos.sh
open dist/Cpython_interpreter.app
```

## Dopo l'install

```bash
cpy run tuoFile.cpy
# oppure
open -a Cpython_interpreter
```

- Demone: LaunchAgent `com.cpython.interpreter` (login)
- Dati: `~/Library/Application Support/CPython`
- Estensione editor: VS Code / Cursor

## Note firma / Gatekeeper

Senza Apple Developer ID, al primo avvio macOS puo' bloccare l'app:
**Impostazioni di Sistema → Privacy e sicurezza → Apri comunque**.
Per distribuzione pubblica serve notarizzazione Apple (fase successiva).

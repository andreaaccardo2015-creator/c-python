# C Python e gli antivirus (falsi positivi)

**Riepilogo: `CPython_Setup.exe` non è un virus.** È l'installer open source del
linguaggio C Python, compilato pubblicamente da GitHub Actions a partire dal
codice sorgente che trovi in questo repository, sotto licenza MIT.

Alcuni antivirus (soprattutto Windows Defender, 360 安全卫士, 腾讯电脑管家 e
altri motori euristici) lo segnalano comunque. Questo documento spiega **perché**
succede, **cosa fa esattamente** il programma, e **come verificare** che il file
che hai scaricato sia autentico.

- Sorgenti: <https://github.com/andreaaccardo2015-creator/c-python>
- Licenza: [MIT](LICENSE) — Copyright (c) 2026 Andrea Accardo
- Autore/contatto: apri una issue su GitHub

---

## 1. Perché viene segnalato

La segnalazione è **euristica**, non basata su una firma di malware reale. Le
cause, in ordine di peso:

1. **È un eseguibile PyInstaller.** PyInstaller impacchetta l'interprete Python
   e il codice in un unico `.exe` che, all'avvio, si autoestrae in una cartella
   temporanea. Questo schema "unpack ed esegui" è identico a quello usato dai
   packer malevoli, quindi molti motori lo trattano come sospetto a prescindere
   dal contenuto. È il falso positivo più diffuso del mondo Python.
2. **Non è firmato digitalmente.** Un certificato di code signing costa
   centinaia di euro l'anno; questo è un progetto gratuito e non ne ha uno. Per
   Windows SmartScreen un binario senza firma e senza reputazione è
   automaticamente "sconosciuto".
3. **Si registra all'avvio automatico.** Serve al demone in background che
   tiene attive le associazioni dei file `.cpy`. È un comportamento legittimo
   ma identico alla persistenza di un malware.
4. **Scrive nel registro di Windows.** Per associare i file `.cpy`/`.cp` e per
   aggiungere `cpy` al `PATH` dell'utente.
5. **Si copia in un'altra cartella e avvia altri processi.** L'installer copia
   se stesso in `%LOCALAPPDATA%` e lancia PowerShell per installare l'estensione
   dell'editor. Anche questa combinazione è un classico pattern euristico.

Nessuno di questi comportamenti è nascosto: sono tutti visibili nel sorgente,
principalmente in [`daemon/install.py`](daemon/install.py) e
[`daemon/associate_win.py`](daemon/associate_win.py).

## 2. Cosa fa esattamente il programma

Elenco completo e verificabile delle modifiche al sistema.

**File** (nessuna scrittura fuori dal profilo utente, nessun privilegio di
amministratore richiesto):

- `%LOCALAPPDATA%\CPythonInterpreter\` — runtime, librerie, icone e una copia
  dell'eseguibile.
- `%LOCALAPPDATA%\CPythonInterpreter\bin\cpy.bat` — il comando `cpy`.
- `%USERPROFILE%\.vscode\extensions\` e `%USERPROFILE%\.cursor\extensions\` —
  estensione per l'evidenziazione della sintassi `.cpy`.

**Registro di sistema** (solo `HKEY_CURRENT_USER`, mai `HKEY_LOCAL_MACHINE`):

- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` → valore
  `CPythonInterpreter`, per avviare il demone al login.
- `HKCU\Environment` → aggiunge la cartella `bin` alla variabile `Path`.
- `HKCU\Software\Classes\.cpy`, `.cp` e `CPython.File` → associazione dei file
  e icona.

**Rete:**

- Il demone apre un server HTTP **solo su `127.0.0.1:39271`** (loopback), usato
  dall'editor per comunicare con l'interprete. Non è raggiungibile dall'esterno.
- Il programma **non** contatta alcun server remoto, non invia telemetria, non
  scarica ed esegue codice da internet.

**Processi avviati:**

- `powershell.exe` una sola volta durante l'installazione, per copiare
  l'estensione dell'editor (script in `tools/installa_estensione_vscode.ps1`).
- Se stesso con `--daemon`, come processo in background.

## 3. Cosa NON fa

Non cifra, non rinomina e non cancella i tuoi file. Non legge documenti,
password, cookie o portafogli. Non installa driver o servizi di sistema. Non
richiede privilegi di amministratore. Non apre porte verso l'esterno. Non
contiene codice offuscato, downloader o payload compressi oltre al normale
impacchettamento PyInstaller.

Per disinstallare tutto: `cpy uninstall`, poi cancella la cartella
`%LOCALAPPDATA%\CPythonInterpreter`.

## 4. Verificare che il file sia autentico

Ogni release pubblica l'impronta SHA256 dell'installer, sia nelle note della
release sia nel file `CPython_Setup.exe.sha256` allegato.

Su Windows, in PowerShell:

```powershell
Get-FileHash .\CPython_Setup.exe -Algorithm SHA256
```

Confronta il risultato con quello pubblicato sulla
[pagina delle release](https://github.com/andreaaccardo2015-creator/c-python/releases).
Se coincide, stai eseguendo esattamente il file compilato da GitHub Actions; se
non coincide, **non eseguirlo** e segnalalo con una issue.

Puoi anche caricare il file su [VirusTotal](https://www.virustotal.com/) per
vedere quanti motori lo segnalano: tipicamente pochi motori euristici su oltre
settanta, il che è la firma classica di un falso positivo.

La build è pubblica e ricostruibile: il workflow
[`.github/workflows/build.yml`](.github/workflows/build.yml) mostra ogni
comando eseguito per produrre l'eseguibile, e i log di ogni build restano
consultabili nella scheda Actions del repository.

## 5. Come sbloccare il file

Prima di tutto **verifica l'hash** come sopra. Poi:

**Windows Defender / Sicurezza di Windows**
Sicurezza di Windows → Protezione da virus e minacce → Gestisci impostazioni →
Esclusioni → Aggiungi un'esclusione → Cartella → `%LOCALAPPDATA%\CPythonInterpreter`.
Se SmartScreen blocca l'avvio, clicca "Ulteriori informazioni" → "Esegui
comunque".

**360 安全卫士 (360 Total Security)**
安全防护中心 → 信任与拦截 → 信任区 → 添加文件/目录, e aggiungi la cartella
`%LOCALAPPDATA%\CPythonInterpreter`.

**腾讯电脑管家 (Tencent PC Manager)**
病毒查杀 → 信任区 → 添加信任文件.

**火绒 (Huorong)**
病毒查杀 → 信任区 → 添加文件.

**Altri antivirus:** cerca la voce "esclusioni", "whitelist", "quarantena" o
"trusted zone" e aggiungi la cartella di installazione.

## 6. Segnalare il falso positivo al produttore

Questo è il passo che risolve il problema per tutti, non solo sul tuo PC. La
segnalazione è gratuita e di solito viene lavorata in pochi giorni. Allega
sempre il file, il link al repository e questo documento.

| Antivirus | Dove segnalare |
| --- | --- |
| Microsoft Defender | <https://www.microsoft.com/en-us/wdsi/filesubmission> |
| 360 Total Security | <https://open.360.cn/rescue.html> oppure `virus_report@360.cn` |
| Tencent PC Manager | <https://habo.qq.com/> |
| Huorong 火绒 | <https://www.huorong.cn/person5.html> |
| Kaspersky | <https://opentip.kaspersky.com/> |
| Avast / AVG | <https://www.avast.com/false-positive-file-form.php> |
| Bitdefender | <https://www.bitdefender.com/consumer/support/answer/29358/> |
| ESET | `samples@eset.com` |
| Norton | <https://submit.norton.com/> |
| McAfee | <https://www.mcafee.com/enterprise/en-us/threat-center/threat-library/sample-submission.html> |
| Malwarebytes | <https://www.malwarebytes.com/false-positive> |
| Sophos | <https://support.sophos.com/support/s/filesubmission> |
| Trend Micro | <https://www.trendmicro.com/vinfo/us/threat-encyclopedia/submission-form> |

---

## For antivirus vendors and analysts (English)

`CPython_Setup.exe` (also distributed as `Cpython-interpreter_64x_win.exe`) is
the installer for **C Python**, an open source programming language and
interpreter released under the MIT license.

- Source code: <https://github.com/andreaaccardo2015-creator/c-python>
- Build pipeline: GitHub Actions, `.github/workflows/build.yml`, public logs
- Packaging: PyInstaller one-file, **no UPX compression**, embedded version
  resource identifying product and publisher
- Publisher: Andrea Accardo (independent developer, no code signing
  certificate)

**Why heuristics fire:** PyInstaller self-extracting layout, absence of a code
signing certificate, `HKCU\...\CurrentVersion\Run` autostart entry for the
background daemon, `HKCU\Environment` PATH modification, file association keys,
self-copy into `%LOCALAPPDATA%`, and a one-time `powershell.exe` invocation to
install the editor extension.

**Observed behaviour is limited to:** writing under `%LOCALAPPDATA%\CPythonInterpreter`
and the user's VS Code/Cursor extension directories; creating the
`HKEY_CURRENT_USER` keys listed above; binding an HTTP server on
`127.0.0.1:39271` (loopback only); spawning itself with `--daemon`. There is no
outbound network traffic, no telemetry, no remote code download, no credential
or file access outside its own installation directory, no privilege escalation,
and no obfuscated code.

The relevant logic is readable in `daemon/install.py`, `daemon/associate_win.py`
and `daemon/server.py`. We would be grateful if you could whitelist the file or
adjust the detection. Please contact us through GitHub issues for samples of
future releases.

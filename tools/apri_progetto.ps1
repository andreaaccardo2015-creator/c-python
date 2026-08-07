param(
    [Parameter(Mandatory = $true)]
    [string]$CPythonHome
)

Add-Type -AssemblyName System.Windows.Forms | Out-Null

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Seleziona la cartella del progetto C Python"
$dialog.ShowNewFolderButton = $true
if (Test-Path $CPythonHome) {
    $dialog.SelectedPath = $CPythonHome
}

if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    exit 1
}

$project = $dialog.SelectedPath
if (-not (Test-Path $project)) {
    Write-Host "Cartella non valida."
    exit 1
}

# Installa/aggiorna estensione VS Code con logo ufficiale
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $CPythonHome "tools\installa_estensione_vscode.ps1") -CPythonHome $CPythonHome | Out-Host

$vscodeDir = Join-Path $project ".vscode"
New-Item -ItemType Directory -Force -Path $vscodeDir | Out-Null

$settingsJson = @"
{
  "files.associations": {
    "*.cpy": "cpython",
    "*.cp": "cpython"
  },
  "files.encoding": "utf8",
  "editor.insertSpaces": true,
  "editor.tabSize": 4,
  "window.title": "C Python — \${dirty}\${activeEditorShort}\${separator}\${rootName}",
  "workbench.colorCustomizations": {
    "titleBar.activeBackground": "#2f5fad",
    "titleBar.activeForeground": "#ffffff",
    "titleBar.inactiveBackground": "#254a88",
    "titleBar.inactiveForeground": "#d7e4ff",
    "activityBar.background": "#1c335c",
    "activityBar.foreground": "#ffffff",
    "statusBar.background": "#2f5fad",
    "statusBar.foreground": "#ffffff"
  },
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "$($CPythonHome.Replace('\', '\\'))",
    "CPYTHON_HOME": "$($CPythonHome.Replace('\', '\\'))"
  }
}
"@
Set-Content -Path (Join-Path $vscodeDir "settings.json") -Value $settingsJson -Encoding UTF8

$tasksJson = @"
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Esegui C Python (file corrente)",
      "type": "shell",
      "command": "$($CPythonHome.Replace('\', '\\'))\\cpython.bat",
      "args": ["`${file}"],
      "options": {
        "cwd": "`${workspaceFolder}",
        "env": {
          "PYTHONPATH": "$($CPythonHome.Replace('\', '\\'))",
          "CPYTHON_HOME": "$($CPythonHome.Replace('\', '\\'))"
        }
      },
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    }
  ]
}
"@
Set-Content -Path (Join-Path $vscodeDir "tasks.json") -Value $tasksJson -Encoding UTF8

$extRec = @"
{
  "recommendations": ["cpython.c-python"]
}
"@
Set-Content -Path (Join-Path $vscodeDir "extensions.json") -Value $extRec -Encoding UTF8

$guidePath = Join-Path $project "LEGGIMI_C_PYTHON.txt"
if (-not (Test-Path $guidePath)) {
    @"
Progetto C Python
=================

1. Crea un file con estensione .cpy  (esempio: gioco.cpy)
2. Scrivi il codice C Python
3. Apri il file .cpy e premi Ctrl+Shift+B
   oppure: Terminal > Run Task > Esegui C Python (file corrente)

Nella barra laterale sinistra trovi l'icona C Python (logo).
Interprete: $CPythonHome
"@ | Set-Content -Path $guidePath -Encoding UTF8
}

$sample = Join-Path $project "ciao.cpy"
if (-not (Test-Path $sample)) {
    @"
// ciao.cpy - primo programma C Python
print.log("Ciao da C Python!")
"@ | Set-Content -Path $sample -Encoding UTF8
}

# Logo nel progetto
$logoSrc = Join-Path $CPythonHome "logo.png"
$logoDst = Join-Path $project "c_python_logo.png"
if (Test-Path $logoSrc) {
    Copy-Item -Force $logoSrc $logoDst
}

# README con logo (si apre bene in preview)
$readme = Join-Path $project "README.md"
@"
# C Python

![C Python logo](c_python_logo.png)

Crea file **``.cpy``** e premi **Ctrl+Shift+B** per eseguire.
"@ | Set-Content -Path $readme -Encoding UTF8

Write-Host ""
Write-Host "Apertura VS Code in: $project"
Write-Host "Logo C Python attivo (welcome + barra laterale)."
Write-Host "Esegui con Ctrl+Shift+B."
Write-Host ""

# Riavvia/carica estensioni e apre welcome
& code --new-window "$project"
Start-Sleep -Seconds 2
& code "$project" --command "cpython.showWelcome"
exit 0

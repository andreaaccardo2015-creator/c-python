param(
    [Parameter(Mandatory = $true)]
    [string]$CPythonHome
)

$extSrc = Join-Path $CPythonHome "editors\vscode-c-python"
if (-not (Test-Path (Join-Path $extSrc "package.json"))) {
    Write-Host "Estensione editor non trovata: $extSrc"
    return $false
}

function Install-ToExtRoot([string]$extRoot) {
    New-Item -ItemType Directory -Force -Path $extRoot | Out-Null
    $dest = Join-Path $extRoot "cpython.c-python-0.2.3"

    foreach ($oldName in @("cpython.c-python-0.1.0", "cpython.c-python-0.2.0", "cpython.c-python-0.2.1", "cpython.c-python-0.2.2")) {
        $old = Join-Path $extRoot $oldName
        if (Test-Path $old) {
            Remove-Item -Recurse -Force $old
        }
    }

    if (Test-Path $dest) {
        Remove-Item -Recurse -Force $dest
    }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Recurse -Force (Join-Path $extSrc "*") $dest

    $logo = Join-Path $CPythonHome "logo.png"
    if (Test-Path $logo) {
        $media = Join-Path $dest "media"
        New-Item -ItemType Directory -Force -Path $media | Out-Null
        Copy-Item -Force $logo (Join-Path $media "logo.png")
        $iconOut = Join-Path $media "icon.png"
        & python -c "from PIL import Image; Image.open(r'$logo').convert('RGBA').resize((128,128), Image.Resampling.LANCZOS).save(r'$iconOut')"
    }

    Write-Host "Estensione C Python installata in: $dest"
}

Install-ToExtRoot (Join-Path $env:USERPROFILE ".vscode\extensions")

$cursorExt = Join-Path $env:USERPROFILE ".cursor\extensions"
if (Test-Path (Join-Path $env:USERPROFILE ".cursor")) {
    Install-ToExtRoot $cursorExt
}

return $true

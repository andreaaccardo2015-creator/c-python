param(
    [Parameter(Mandatory = $true)]
    [string]$CPythonHome
)

$bat = Join-Path $CPythonHome "Avvia_C_Python.bat"
$ico = Join-Path $CPythonHome "logo.ico"
$lnkPath = Join-Path $CPythonHome "C Python.lnk"

if (-not (Test-Path $bat)) {
    Write-Error "Avvia_C_Python.bat non trovato"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = $bat
$lnk.WorkingDirectory = $CPythonHome
$lnk.WindowStyle = 1
$lnk.Description = "C Python - interprete e editor"
if (Test-Path $ico) {
    $lnk.IconLocation = "$ico,0"
}
$lnk.Save()

# Collegamento anche sul Desktop (se possibile)
$desktop = [Environment]::GetFolderPath("Desktop")
if ($desktop -and (Test-Path $desktop)) {
    $deskLnk = Join-Path $desktop "C Python.lnk"
    Copy-Item -Force $lnkPath $deskLnk
}

Write-Host "Collegamento creato con logo: $lnkPath"
exit 0

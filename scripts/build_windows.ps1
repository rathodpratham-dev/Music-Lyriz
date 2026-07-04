param(
    [switch]$OneFile,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$BuildVenv = Join-Path $Root ".venv-build"
$Python = Join-Path $BuildVenv "Scripts\python.exe"
$DistExe = Join-Path $Root "dist\Music Lyriz\Music Lyriz.exe"
$PortableExe = Join-Path $Root "dist\Music Lyriz Portable.exe"
$IsccCandidates = @(
    $env:INNO_SETUP_ISCC,
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

Set-Location -LiteralPath $Root

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Assert-NotLocked {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
        $stream.Close()
    }
    catch {
        throw "Close Music Lyriz before building. Locked file: $Path"
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    python -m venv $BuildVenv
}

Invoke-Checked { & $Python -m pip install --upgrade pip } "Upgrade pip"
Invoke-Checked { & $Python -m pip install -r requirements.txt pyinstaller } "Install build dependencies"
Invoke-Checked { & $Python packaging\make_icon.py } "Generate app icon"

if ($OneFile) {
    Assert-NotLocked $PortableExe
    Invoke-Checked { & $Python -m PyInstaller --clean --noconfirm packaging\music_lyriz_onefile.spec } "Build portable app"
    Write-Host "Built portable EXE: dist\Music Lyriz Portable.exe"
    exit 0
}

Assert-NotLocked $DistExe
Invoke-Checked { & $Python -m PyInstaller --clean --noconfirm packaging\music_lyriz.spec } "Build app"

if ($SkipInstaller) {
    Write-Host "Built app folder: dist\Music Lyriz"
    exit 0
}

if (-not $IsccCandidates) {
    Write-Warning "Inno Setup compiler was not found. Install Inno Setup, then rerun this script to create the installer."
    Write-Host "Built app folder: dist\Music Lyriz"
    exit 0
}

$Iscc = $IsccCandidates[0]
Invoke-Checked { & $Iscc packaging\music_lyriz.iss } "Build installer"
Write-Host "Built installer: dist\installer"

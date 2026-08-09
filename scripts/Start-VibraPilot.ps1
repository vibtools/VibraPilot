param(
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $ExePath) {
    $Candidate = Join-Path $Root "dist\VibraPilot\VibraPilot.exe"
    if (Test-Path $Candidate) {
        $ExePath = $Candidate
    } else {
        $ExePath = Join-Path $Root "release\VibraPilot-1.0.6.7-Windows-x64\VibraPilot.exe"
    }
}

if (-not (Test-Path $ExePath)) {
    throw "VibraPilot.exe was not found. Build the project first with: py -3.12 build.py"
}

Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath)

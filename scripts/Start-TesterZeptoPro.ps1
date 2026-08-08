param(
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $ExePath) {
    $Candidate = Join-Path $Root "dist\TesterZeptoPro\TesterZeptoPro.exe"
    if (Test-Path $Candidate) {
        $ExePath = $Candidate
    } else {
        $ExePath = Join-Path $Root "release\TesterZeptoPro-1.0.6.1-Windows-x64\TesterZeptoPro.exe"
    }
}

if (-not (Test-Path $ExePath)) {
    throw "TesterZeptoPro.exe was not found. Build the project first with: py -3.12 build.py"
}

Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath)

# Jarvis Setup — installs Copilot instructions to VS Code user prompts folder
# Run once on any Windows machine after cloning the repo.
# Usage: Right-click -> "Run with PowerShell"  OR  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

$RAW_URL = "https://raw.githubusercontent.com/EnzoMadjos/EnzoRepo/main/.github/jarvis.instructions.md"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOCAL_FILE = Join-Path $SCRIPT_DIR ".github\jarvis.instructions.md"

$DEST_DIRS = @(
    "$env:APPDATA\Code\User\prompts",          # VS Code stable
    "$env:APPDATA\Code - Insiders\User\prompts" # VS Code Insiders
)

$installed = $false

foreach ($dir in $DEST_DIRS) {
    $parentExists = Test-Path (Split-Path -Parent $dir)
    if ($parentExists) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $dest = Join-Path $dir "jarvis.instructions.md"
        if (Test-Path $LOCAL_FILE) {
            Copy-Item $LOCAL_FILE $dest -Force
        } else {
            Invoke-WebRequest -Uri $RAW_URL -OutFile $dest -UseBasicParsing
        }
        Write-Host "✔ Installed to $dir" -ForegroundColor Green
        $installed = $true
    }
}

if (-not $installed) {
    Write-Host "⚠ No VS Code User/prompts folder found. Install VS Code first, then re-run." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Done. Restart VS Code — Jarvis + Avengers team are now active in every workspace." -ForegroundColor Cyan

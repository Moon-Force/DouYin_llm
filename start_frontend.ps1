$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
Set-Location $frontend

$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not $npm) {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
}

if (-not $node) {
    Write-Host "Node.js not found in PATH"
    exit 1
}

if (-not $npm) {
    Write-Host "npm not found in PATH"
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    & $npm.Source install
}

Write-Host "Starting frontend dev server..."
& $npm.Source run dev -- --host 127.0.0.1 --strictPort --port 5173

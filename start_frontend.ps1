$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
Set-Location $frontend

$node = "C:\Program Files\nodejs\node.exe"
$npmCli = "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"

if (-not (Test-Path $node)) {
    Write-Host "Node.js not found at $node"
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    & $node $npmCli install
}

Write-Host "Starting frontend dev server..."
& $node $npmCli run dev -- --host 127.0.0.1 --strictPort --port 5173

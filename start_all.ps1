$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Host "Missing .env file. Copy .env.example to .env and fill DASHSCOPE_API_KEY first."
    exit 1
}

Write-Host "Starting backend in a new PowerShell window..."
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $root "start_backend_qwen.ps1")

Write-Host "Starting frontend in a new PowerShell window..."
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $root "start_frontend.ps1")

Write-Host "All services launched. Backend now includes the built-in collector."

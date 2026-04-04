$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Host "Missing .env file. Copy .env.example to .env and fill DASHSCOPE_API_KEY first."
    exit 1
}

Write-Host "Starting backend with Qwen online mode..."
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

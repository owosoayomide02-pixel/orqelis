# Orqelis local development setup (Windows). Docker is optional; SQLite is the default.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. "$PSScriptRoot\env-path.ps1"

$python = Get-OrqelisPython
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Error "Node.js 20+ / npm is not on PATH. Install it from https://nodejs.org/ then re-run this script."
}

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "Using Python: $python"
& $python -m pip install -e ".\packages\security"
& $python -m pip install -e ".\packages\shared"
& $python -m pip install -e ".\services\detection"
& $python -m pip install -e ".\services\ai"
& $python -m pip install -e ".\services\api[dev]"
& $python -m pip install -e ".\apps\agent-windows[dev]"

Push-Location ".\apps\web"; npm install; Pop-Location
Push-Location ".\apps\admin"; npm install; Pop-Location

Write-Host "Setup complete. Docker is not required (SQLite is already configured in .env)."
Write-Host "API:   cd services\api; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host "Web:   cd apps\web; npm run dev"
Write-Host "Admin: cd apps\admin; npm run dev"
Write-Host "Agent: cd apps\agent-windows; python -m orqelis_agent enroll --code NNNNNN"

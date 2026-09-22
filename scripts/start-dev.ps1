# Start API, web, and admin for local Orqelis development (SQLite, no Docker).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\env-path.ps1"
Set-Location $root

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\services\api'; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\apps\web'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\apps\admin'; npm run dev"

Write-Host "Started API :8000, web :3000, admin :3001"

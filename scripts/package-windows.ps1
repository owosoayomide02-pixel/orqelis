# Requires: Python 3.11+ with pip, and PyInstaller (`pip install pyinstaller`)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\apps\agent-windows"
python -m pip install -e .
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --name orqelis-agent-windows --hidden-import orqelis_agent.platforms.windows --hidden-import orqelis_agent.platforms.linux --hidden-import orqelis_agent.platforms.macos orqelis_agent/__main__.py
Write-Host "Built dist/orqelis-agent-windows.exe"

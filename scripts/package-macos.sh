#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/agent-windows"
python3 -m pip install -e .
python3 -m pip install pyinstaller
python3 -m PyInstaller --noconfirm --onefile --name orqelis-agent-macos \
  --hidden-import orqelis_agent.platforms.windows \
  --hidden-import orqelis_agent.platforms.linux \
  --hidden-import orqelis_agent.platforms.macos \
  orqelis_agent/__main__.py
echo "Built dist/orqelis-agent-macos"

# Orqelis endpoint agent

Telemetry-only agent for **Windows, macOS, and Linux**. It does not open a remote shell, write user files, or launch applications on command.

The same Python package selects platform collectors at runtime:

- Windows: Security event log, Defender, firewall, services
- macOS: Gatekeeper, application firewall, unified log snippets, launchctl
- Linux: auth.log/journal failed logons, ufw/firewalld, systemd service state

## Install notice

Orqelis Endpoint Security collects security telemetry necessary to provide endpoint protection and security monitoring.

By installing this agent, you confirm that you are authorized to install and operate it on this device.

## Enroll

```powershell
cd orqelis/apps/agent-windows
python -m pip install -e .
python -m orqelis_agent enroll --code 123456 --api http://127.0.0.1:8000
python -m orqelis_agent run
```

On macOS or Linux, use the same commands from a terminal after `pip install -e .`.

## Packaged builds

See `scripts/` in the repo root:

- `scripts/package-windows.ps1`
- `scripts/package-macos.sh`
- `scripts/package-linux.sh`

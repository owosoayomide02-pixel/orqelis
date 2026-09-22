# Endpoint agent guide

The same `orqelis_agent` package runs on Windows, macOS, and Linux. It stores `device_token` under the user profile in `.orqelis/agent.json`.

Install only on devices you own or are authorized to manage. The agent collects listed security telemetry only.

See `apps/agent-windows/README.md` and the Linux/macOS notes in `apps/agent-linux` and `apps/agent-macos`. Packaged binaries can be built with `scripts/package-windows.ps1`, `scripts/package-macos.sh`, and `scripts/package-linux.sh`.

# Orqelis Linux agent

This is the Linux distribution of the shared Orqelis endpoint agent. Implementation lives in [`../agent-windows`](../agent-windows) (`orqelis_agent.platforms.linux`).

```bash
cd ../agent-windows
python3 -m pip install -e .
python3 -m orqelis_agent enroll --code 123456 --api http://127.0.0.1:8000
python3 -m orqelis_agent run
```

Package with `../../../scripts/package-linux.sh`.

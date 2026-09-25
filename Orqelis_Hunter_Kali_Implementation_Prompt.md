# Orqelis — Hunter Scan Implementation (Kali Integration)

Paste this into Cursor against the Orqelis repo. Implement **Option A first, completely, and confirm it works** before touching Option B. Do not build both simultaneously.

---

## OPTION A — Kali tools inside the existing API container (implement this first)

### Task 1: Update `infrastructure/docker/api.Dockerfile`

Add tool installation before the existing Python package install steps. Keep everything already in this file — only insert the block below.

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nmap build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSfL https://raw.githubusercontent.com/projectdiscovery/subfinder/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/httpx/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/nuclei/main/install.sh | sh -s -- -b /usr/local/bin

RUN nuclei -update-templates

# --- existing Dockerfile content continues below unchanged (package installs, CMD) ---
```

### Task 2: Create `services/api/app/scanner.py`

```python
import subprocess
import json
import asyncio
from datetime import datetime

class ScanTimeoutError(Exception):
    pass

async def run_tool(cmd: list[str], timeout_s: int, stdin_data: str | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if stdin_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_data.encode() if stdin_data else None),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise ScanTimeoutError(f"{cmd[0]} exceeded {timeout_s}s")
    return stdout.decode()

async def run_hunter_scan(domain: str) -> dict:
    results = {"tools_run": [], "raw_output": {}, "errors": []}

    try:
        subfinder_out = await run_tool(["subfinder", "-d", domain, "-silent"], timeout_s=120)
        results["tools_run"].append("subfinder")
        results["raw_output"]["subfinder"] = subfinder_out
    except ScanTimeoutError as e:
        results["errors"].append(str(e))
        subfinder_out = domain

    try:
        httpx_out = await run_tool(["httpx", "-silent", "-json"], timeout_s=60, stdin_data=subfinder_out)
        results["tools_run"].append("httpx")
        results["raw_output"]["httpx"] = httpx_out
    except ScanTimeoutError as e:
        results["errors"].append(str(e))
        httpx_out = f"https://{domain}\n"

    try:
        nuclei_out = await run_tool(
            ["nuclei", "-jsonl", "-severity", "medium,high,critical"],
            timeout_s=300,
            stdin_data=httpx_out,
        )
        results["tools_run"].append("nuclei")
        results["raw_output"]["nuclei"] = nuclei_out
    except ScanTimeoutError as e:
        results["errors"].append(str(e))

    return results

def parse_nuclei_output(raw: str) -> list[dict]:
    findings = []
    for line in raw.strip().splitlines():
        if not line:
            continue
        data = json.loads(line)
        findings.append({
            "title": data["info"]["name"],
            "description": data["info"].get("description", ""),
            "severity": data["info"]["severity"],
            "tool_source": "nuclei",
            "raw_reference": {
                "template_id": data.get("template-id"),
                "matched_at": data.get("matched-at"),
            },
        })
    return findings
```

### Task 3: Wire into the API router

Add to the appropriate existing router file under `services/api/app/routers/` (follow the existing router pattern in this codebase for auth/dependency injection style — do not invent a new pattern):

```python
from app.scanner import run_hunter_scan, parse_nuclei_output

@router.post("/web-assets/{id}/scan")
async def start_scan(id: UUID, db: AsyncSession = Depends(get_db)):
    web_asset = await get_verified_web_asset_or_403(id, db)  # must 403 if not verified — see merge spec Part 2.3
    scan_job = await create_scan_job(web_asset.id, db)

    raw_results = await run_hunter_scan(web_asset.domain)
    findings = parse_nuclei_output(raw_results["raw_output"].get("nuclei", ""))

    for finding in findings:
        await insert_event(source="web_asset", source_id=web_asset.id, **finding, db=db)

    await mark_scan_completed(scan_job.id, raw_results, db)
    return {"scan_job_id": scan_job.id, "findings_count": len(findings)}
```

Implement `get_verified_web_asset_or_403`, `create_scan_job`, `insert_event`, `mark_scan_completed` against the existing `WebAsset`/`ScanJob` models and the existing events table, following the data model already specified in `Orqelis_Full_Merge_Specification.md` (Parts 1 and 2). Reuse existing DB session/dependency patterns already in `services/api` — do not create a second database access pattern.

### Task 4: Local verification before deploy

Run locally:
```bash
cd services/api
python -m uvicorn app.main:app --reload --port 8000
```
Trigger a test scan against a known-safe test target (do not scan a real unverified domain):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/web-assets/{id}/scan
```
`nuclei`/`subfinder`/`httpx` will only be present once running inside the built Docker image — if testing without Docker locally, either install the same tools locally via the ProjectDiscovery install scripts, or skip local testing and verify directly after deploy.

### Task 5: Deploy

`render.yaml` already targets `infrastructure/docker/api.Dockerfile` — pushing to the connected branch triggers a rebuild. First deploy after this change will take noticeably longer (nuclei template download) — this is expected, not a failure.

**Do not proceed to Option B until a real scan against a verified test domain returns findings that land correctly in the events table.**

---

## OPTION B — Standalone scanner VM (only after Option A is confirmed working)

### Task 1: Create `scanner-service/` as a new top-level directory (not under `apps/` or `services/api` — this deploys separately)

```
scanner-service/
├── Dockerfile
├── main.py
└── scanner.py   # identical to services/api/app/scanner.py — copy it, do not import cross-service
```

### Task 2: `scanner-service/Dockerfile`

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl nmap ca-certificates && rm -rf /var/lib/apt/lists/*
RUN curl -sSfL https://raw.githubusercontent.com/projectdiscovery/subfinder/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/httpx/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/nuclei/main/install.sh | sh -s -- -b /usr/local/bin \
    && nuclei -update-templates
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn httpx
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
```

### Task 3: `scanner-service/main.py`

```python
from fastapi import FastAPI, Header, HTTPException
from scanner import run_hunter_scan, parse_nuclei_output
import os

app = FastAPI()
INTERNAL_TOKEN = os.environ["SCANNER_INTERNAL_TOKEN"]

@app.post("/run-scan")
async def run_scan(domain: str, x_internal_token: str = Header(...)):
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(403)
    raw = await run_hunter_scan(domain)
    return {"findings": parse_nuclei_output(raw["raw_output"].get("nuclei", ""))}
```

### Task 4: Add a remote-call variant to `services/api/app/scanner.py`

```python
import httpx as http_client
import os

async def run_hunter_scan_remote(domain: str) -> dict:
    async with http_client.AsyncClient(timeout=400) as client:
        resp = await client.post(
            f"{os.environ['SCANNER_SERVICE_URL']}/run-scan",
            params={"domain": domain},
            headers={"x-internal-token": os.environ["SCANNER_INTERNAL_TOKEN"]},
        )
        resp.raise_for_status()
        return resp.json()
```

Add `SCANNER_SERVICE_URL` and `SCANNER_INTERNAL_TOKEN` to `.env.example` and the production environment config.

### Task 5: Switch the router to call the remote version

In the `start_scan` endpoint from Option A Task 3, replace the direct `run_hunter_scan(...)` call with `run_hunter_scan_remote(...)`. Everything downstream (parsing, event insertion) stays the same — only the scan-execution call site changes.

### Non-goals for this task

- Do not deploy `scanner-service/` to Render — it is a separate VM (Oracle Cloud free tier), not part of the existing Render/Netlify deploy targets
- Do not expose port 9000 publicly — restrict inbound access to Render's outbound IP range plus the internal token check
- Do not remove the direct (Option A) `run_hunter_scan` function — keep both available; only the router's call site switches

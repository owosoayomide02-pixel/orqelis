"""Orqelis scanner-service — Option B standalone Hunter VM (not deployed to Render)."""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, Query
from scanner import parse_nuclei_output, run_hunter_scan

app = FastAPI(title="Orqelis Scanner Service", version="0.1.0")

INTERNAL_TOKEN = os.environ.get("SCANNER_INTERNAL_TOKEN", "")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "orqelis-scanner"}


@app.post("/run-scan")
async def run_scan(
    domain: str = Query(..., min_length=3, max_length=253),
    x_internal_token: str = Header(...),
) -> dict:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    raw = await run_hunter_scan(domain.strip().lower())
    # Full raw result for API persist path + parsed nuclei findings for convenience
    return {
        **raw,
        "findings": parse_nuclei_output((raw.get("raw_output") or {}).get("nuclei", "")),
    }

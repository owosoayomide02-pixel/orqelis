"""Remote Hunter calls (Option B) — scanner-service VM."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


async def run_hunter_scan_remote(domain: str) -> dict[str, Any]:
    base = (settings.scanner_service_url or "").rstrip("/")
    token = settings.scanner_internal_token or ""
    if not base or not token:
        return {
            "tools_run": [],
            "raw_output": {},
            "errors": ["SCANNER_SERVICE_URL / SCANNER_INTERNAL_TOKEN not configured"],
            "status": "failed",
            "error_message": "Remote scanner is not configured",
        }
    async with httpx.AsyncClient(timeout=400.0) as client:
        resp = await client.post(
            f"{base}/run-scan",
            params={"domain": domain},
            headers={"x-internal-token": token},
        )
        resp.raise_for_status()
        data = resp.json()
    # Normalize to execute_scan shape (service may return findings + raw)
    if "raw_output" not in data and "findings" in data:
        return {
            "tools_run": data.get("tools_run") or ["remote"],
            "raw_output": {"nuclei": ""},
            "errors": [],
            "status": "completed",
            "error_message": None,
            "findings": data.get("findings") or [],
        }
    return data

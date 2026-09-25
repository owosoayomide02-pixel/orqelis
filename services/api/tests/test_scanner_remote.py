"""Option B remote scanner client tests."""

from __future__ import annotations

import pytest

from app.scanner import execute_scan
from app.scanner import remote as remote_mod


@pytest.mark.asyncio
async def test_execute_scan_remote(monkeypatch):
    async def fake_remote(domain: str):
        return {
            "tools_run": ["subfinder", "httpx", "nuclei"],
            "raw_output": {"nuclei": '{"info":{"name":"R","severity":"high"},"template-id":"r"}\n'},
            "errors": [],
            "status": "completed",
            "error_message": None,
            "findings": [
                {
                    "title": "R",
                    "description": "",
                    "severity": "high",
                    "tool_source": "nuclei",
                    "raw_reference": {},
                }
            ],
        }

    monkeypatch.setattr("app.scanner.settings.scanner_mode", "remote")
    monkeypatch.setattr("app.scanner.run_hunter_scan_remote", fake_remote)
    monkeypatch.setattr("app.domain_validation.domain_resolves_to_private", lambda _d: False)
    out = await execute_scan("example.com")
    assert out["status"] == "completed"
    assert out["findings"][0]["title"] == "R"


@pytest.mark.asyncio
async def test_remote_missing_config(monkeypatch):
    monkeypatch.setattr(remote_mod.settings, "scanner_service_url", "")
    monkeypatch.setattr(remote_mod.settings, "scanner_internal_token", "")
    out = await remote_mod.run_hunter_scan_remote("example.com")
    assert out["status"] == "failed"

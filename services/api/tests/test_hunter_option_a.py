"""Unit tests for Option A in-process Hunter runner."""

from __future__ import annotations

import pytest

from app.scanner import execute_scan, normalize_raw
from app.scanner import hunter as hunter_mod


@pytest.mark.asyncio
async def test_run_hunter_scan_chain(monkeypatch):
    calls: list[str] = []

    async def fake_run_tool(cmd, timeout_s, stdin_data=None):
        calls.append(cmd[0])
        if cmd[0] == "subfinder":
            return "example.com\nwww.example.com\napi.example.com\n"
        if cmd[0] == "httpx":
            return (
                '{"url":"https://example.com","status_code":200,"tech":["nginx"]}\n'
                '{"url":"https://www.example.com","status_code":503}\n'
            )
        if cmd[0] == "nmap":
            return "Host: example.com () Ports: 80/open/tcp//http///, 443/open/tcp//https///, 22/open/tcp//ssh///\n"
        if cmd[0] == "nuclei":
            return (
                '{"template-id":"csp","info":{"name":"Missing CSP","description":"x","severity":"medium"},'
                '"matched-at":"https://example.com"}\n'
            )
        return ""

    monkeypatch.setattr(hunter_mod, "run_tool", fake_run_tool)
    monkeypatch.setattr(hunter_mod, "filter_public_hosts", lambda hosts: hosts)

    result = await hunter_mod.run_hunter_scan("example.com")
    assert result["tools_run"] == ["subfinder", "httpx", "nmap", "nuclei"]
    assert "nuclei" in result["raw_output"]
    assert result["status"] == "completed"
    assert calls == ["subfinder", "httpx", "nmap", "nuclei"]

    findings = normalize_raw("example.com", result["raw_output"])
    assert any(f["tool_source"] == "nuclei" for f in findings)


@pytest.mark.asyncio
async def test_execute_scan_local_uses_hunter(monkeypatch):
    async def fake_hunter(domain: str):
        return {
            "tools_run": ["subfinder"],
            "raw_output": {"subfinder": domain},
            "errors": [],
            "status": "completed",
            "error_message": None,
        }

    monkeypatch.setattr("app.scanner.settings.scanner_mode", "local")
    monkeypatch.setattr("app.scanner.run_hunter_scan", fake_hunter)
    monkeypatch.setattr("app.domain_validation.domain_resolves_to_private", lambda _d: False)
    out = await execute_scan("acme.test")
    assert out["tools_run"] == ["subfinder"]


@pytest.mark.asyncio
async def test_run_hunter_scan_timeout_partial(monkeypatch):
    async def fake_run_tool(cmd, timeout_s, stdin_data=None):
        if cmd[0] == "subfinder":
            return "example.com\n"
        if cmd[0] == "httpx":
            raise hunter_mod.ScanTimeoutError("httpx exceeded 60s")
        if cmd[0] == "nmap":
            return "Host: example.com () Ports: 80/open/tcp//http///\n"
        if cmd[0] == "nuclei":
            return (
                '{"template-id":"x","info":{"name":"Finding","severity":"high"},'
                '"matched-at":"https://example.com"}\n'
            )
        return ""

    monkeypatch.setattr(hunter_mod, "run_tool", fake_run_tool)
    monkeypatch.setattr(hunter_mod, "filter_public_hosts", lambda hosts: hosts)

    result = await hunter_mod.run_hunter_scan("example.com")
    assert "subfinder" in result["tools_run"]
    assert "nuclei" in result["tools_run"]
    assert any("httpx" in e for e in result["errors"])

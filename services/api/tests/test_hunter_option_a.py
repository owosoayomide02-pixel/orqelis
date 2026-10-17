"""Unit tests for Option A in-process Hunter runner."""

from __future__ import annotations

import pytest

from app.scanner import execute_scan, mock_scan, normalize_raw
from app.scanner import hunter as hunter_mod


@pytest.mark.asyncio
async def test_run_hunter_scan_chain(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_ffuf", False)
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_wapiti", False)

    async def fake_run_tool(cmd, timeout_s, stdin_data=None):
        calls.append(cmd[0])
        if cmd[0] == "subfinder":
            return "example.com\nwww.example.com\napi.example.com\n"
        if cmd[0] == "amass":
            assert cmd[1:3] == ["enum", "-passive"]
            return "example.com\nblog.example.com\n"
        if cmd[0] == "dnsx":
            assert stdin_data == "example.com\nwww.example.com\napi.example.com\nblog.example.com\n"
            return "example.com [A] [203.0.113.10]\n"
        if cmd[0] == "httpx":
            return (
                '{"url":"https://example.com","status_code":200,"tech":["nginx"]}\n'
                '{"url":"https://www.example.com","status_code":503}\n'
            )
        if cmd[0] == "whatweb":
            assert cmd[-2:] == ["https://example.com", "https://www.example.com"]
            return "https://example.com [200 OK] HTTPServer[nginx]\n"
        if cmd[0] == "tlsx":
            return '{"host":"example.com","port":"443","tls_version":"tls10","expired":true}\n'
        if cmd[0] == "testssl.sh":
            assert cmd[-2:] == ["example.com", "www.example.com"]
            return "TLS 1.0 offered (deprecated)\n"
        if cmd[0] == "katana":
            return "https://example.com/login\nhttps://evil.test/offsite\n"
        if cmd[0] == "gobuster":
            return "https://example.com/login (Status: 200)\nhttps://example.com/admin (Status: 302)\n"
        if cmd[0] == "nikto":
            return '{"host":"https://example.com","results":[{"msg":"X-Frame-Options header missing"}]}\n'
        if cmd[0] == "nmap":
            return "Host: example.com () Ports: 80/open/tcp//http///, 443/open/tcp//https///, 22/open/tcp//ssh///\n"
        if cmd[0] == "nuclei":
            nuclei_stdin.append(stdin_data or "")
            return (
                '{"template-id":"csp","info":{"name":"Missing CSP","description":"x","severity":"medium"},'
                '"matched-at":"https://example.com"}\n'
            )
        return ""

    nuclei_stdin: list[str] = []
    monkeypatch.setattr(hunter_mod, "run_tool", fake_run_tool)
    monkeypatch.setattr(hunter_mod, "filter_public_hosts", lambda hosts: hosts)
    monkeypatch.setattr(hunter_mod.os.path, "isfile", lambda _path: True)

    started: list[str] = []

    async def on_tool(tool: str) -> None:
        started.append(tool)

    result = await hunter_mod.run_hunter_scan("example.com", on_tool=on_tool)
    expected = ["subfinder", "amass", "dnsx", "httpx", "whatweb", "tlsx", "testssl.sh", "katana", "gobuster", "nikto", "nmap", "nuclei"]
    assert result["tools_run"] == expected
    assert result["tools_skipped"] == ["ffuf", "wapiti"]
    assert result["status"] == "completed"
    assert result["raw_output"]["dnsx"]
    assert result["raw_output"]["whatweb"]
    assert calls == expected
    assert started == expected

    assert "https://example.com/login" in nuclei_stdin[0], "crawled URLs feed nuclei"
    assert "evil.test" not in nuclei_stdin[0], "off-scope crawl results are dropped"

    findings = normalize_raw("example.com", result["raw_output"])
    sources = {f["tool_source"] for f in findings}
    assert {"nuclei", "tlsx", "amass", "testssl.sh"} <= sources
    tls_titles = [f["title"] for f in findings if f["tool_source"] == "tlsx"]
    assert any("Expired" in t for t in tls_titles)
    assert any("Deprecated TLS" in t for t in tls_titles)


@pytest.mark.asyncio
async def test_execute_scan_local_uses_hunter(monkeypatch):
    async def fake_hunter(domain: str, on_tool=None):
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


@pytest.mark.asyncio
async def test_active_scanners_only_run_when_operator_enables_them(monkeypatch):
    calls: list[str] = []

    async def fake_run_tool(cmd, timeout_s, stdin_data=None):
        calls.append(cmd[0])
        if cmd[0] == "subfinder":
            return "example.com\n"
        if cmd[0] == "httpx":
            return '{"url":"https://example.com","status_code":200}\n'
        if cmd[0] == "ffuf":
            assert "-rate" in cmd and "5" in cmd
            return '{"results":[]}'
        if cmd[0] == "wapiti":
            assert "-d" in cmd and "1" in cmd
            return '{"vulnerabilities":{}}'
        return ""

    monkeypatch.setattr(hunter_mod, "run_tool", fake_run_tool)
    monkeypatch.setattr(hunter_mod, "filter_public_hosts", lambda hosts: hosts)
    monkeypatch.setattr(hunter_mod.os.path, "isfile", lambda _path: True)
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_ffuf", True)
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_wapiti", True)

    result = await hunter_mod.run_hunter_scan("example.com")
    assert "ffuf" in calls
    assert "wapiti" in calls
    assert "ffuf" in result["tools_run"]
    assert "wapiti" in result["tools_run"]
    assert result["tools_skipped"] == []


def test_mock_scan_includes_dns_and_fingerprint_inventory(monkeypatch):
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_ffuf", False)
    monkeypatch.setattr(hunter_mod.settings, "scanner_enable_wapiti", False)
    result = mock_scan("example.com")
    assert "dnsx" in result["tools_run"]
    assert "whatweb" in result["tools_run"]
    assert result["tools_skipped"] == ["ffuf", "wapiti"]
    findings = normalize_raw("example.com", result["raw_output"])
    inventory = [finding for finding in findings if finding["tool_source"] in {"dnsx", "whatweb"}]
    assert len(inventory) == 2
    assert all(finding["severity"] == "info" for finding in inventory)

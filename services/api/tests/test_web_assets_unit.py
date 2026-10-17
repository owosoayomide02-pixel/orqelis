"""Unit tests for domain validation and Hunter parsers."""

from __future__ import annotations

import json

import pytest

from app.domain_validation import normalize_domain, validate_domain
from app.scanner.parsers import (
    parse_amass_output,
    parse_dnsx_output,
    parse_ffuf_output,
    parse_gobuster_output,
    parse_httpx_output,
    parse_nikto_output,
    parse_nuclei_line,
    parse_nuclei_output,
    parse_subfinder_output,
    parse_testssl_output,
    parse_whatweb_output,
    parse_wapiti_output,
)


def test_validate_domain_accepts_public():
    assert validate_domain("https://Acme-App.com/path") == "acme-app.com"


def test_validate_domain_rejects_ip():
    with pytest.raises(ValueError, match="IP"):
        validate_domain("10.0.0.1")


def test_validate_domain_rejects_localhost():
    with pytest.raises(ValueError):
        validate_domain("localhost")
    with pytest.raises(ValueError):
        validate_domain("evil.local")


def test_normalize_strips_protocol():
    assert normalize_domain("HTTP://Example.COM/") == "example.com"


def test_parse_nuclei_line():
    line = json.dumps(
        {
            "template-id": "csp",
            "info": {"name": "Missing CSP", "description": "no csp", "severity": "medium"},
            "matched-at": "https://example.com",
        }
    )
    finding = parse_nuclei_line(line)
    assert finding is not None
    assert finding["title"] == "Missing CSP"
    assert finding["severity"] == "medium"
    assert finding["tool_source"] == "nuclei"


def test_parse_nuclei_output_skips_junk():
    raw = "not-json\n" + json.dumps({"info": {"name": "X", "severity": "high"}, "template-id": "x"})
    findings = parse_nuclei_output(raw)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_parse_httpx_only_notable():
    boring = json.dumps({"url": "https://a.com", "status_code": 200})
    interesting = json.dumps({"url": "https://b.com", "status_code": 503, "tech": ["iis"]})
    findings = parse_httpx_output(boring + "\n" + interesting)
    assert len(findings) == 1
    assert "503" in findings[0]["title"] or "technologies" in findings[0]["title"].lower() or "iis" in findings[0]["title"].lower()


def test_parse_subfinder_volume_finding():
    lines = "\n".join(json.dumps({"host": f"s{i}.example.com"}) for i in range(6))
    findings = parse_subfinder_output(lines, "example.com")
    assert len(findings) == 1
    assert findings[0]["tool_source"] == "subfinder"


def test_parse_dnsx_records_as_informational_inventory():
    findings = parse_dnsx_output("example.com [A] [203.0.113.10] [AAAA] [2001:db8::1]\n")
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"
    assert findings[0]["tool_source"] == "dnsx"
    assert "not a vulnerability" in findings[0]["description"]


def test_parse_whatweb_fingerprint_as_informational_inventory():
    findings = parse_whatweb_output("https://example.com [200 OK] HTTPServer[nginx] Title[Home]\n")
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"
    assert findings[0]["tool_source"] == "whatweb"
    assert findings[0]["raw_reference"]["plugins"][0]["name"] == "HTTPServer"


def test_parse_amass_only_keeps_root_domain_discoveries():
    findings = parse_amass_output("www.example.com\nevil.test\napi.example.com\n", "example.com")
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"
    assert findings[0]["raw_reference"]["sample"] == ["api.example.com", "www.example.com"]


def test_parse_testssl_weak_protocol():
    findings = parse_testssl_output("TLS 1.0 offered (deprecated)\nTLS 1.3 offered (OK)\n")
    assert len(findings) == 1
    assert findings[0]["severity"] == "medium"
    assert findings[0]["tool_source"] == "testssl.sh"


def test_parse_ffuf_and_wapiti_json():
    ffuf = parse_ffuf_output('{"results":[{"url":"https://example.com/admin","status":200}]}')
    wapiti = parse_wapiti_output('{"vulnerabilities":{"SQL Injection":[{"level":"2","path":"/login","info":"Review input handling"}]}}')
    assert ffuf[0]["severity"] == "info"
    assert ffuf[0]["tool_source"] == "ffuf"
    assert wapiti[0]["severity"] == "medium"
    assert wapiti[0]["tool_source"] == "wapiti"


def test_parse_gobuster_directory_results():
    findings = parse_gobuster_output("/admin (Status: 403) [Size: 123]\n")
    assert len(findings) == 1
    assert findings[0]["tool_source"] == "gobuster"
    assert findings[0]["raw_reference"]["status_code"] == 403


def test_parse_nikto_json_results():
    findings = parse_nikto_output('{"vulnerabilities":[{"msg":"X-Frame-Options header missing"}]}')
    assert len(findings) == 1
    assert findings[0]["tool_source"] == "nikto"
    assert "X-Frame-Options" in findings[0]["title"]

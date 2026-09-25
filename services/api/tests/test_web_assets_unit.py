"""Unit tests for domain validation and Hunter parsers."""

from __future__ import annotations

import json

import pytest

from app.domain_validation import normalize_domain, validate_domain
from app.scanner.parsers import parse_httpx_output, parse_nuclei_line, parse_nuclei_output, parse_subfinder_output


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

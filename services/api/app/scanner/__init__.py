"""Hunter scan runner — local (Option A), mock (tests), docker (legacy Kali image)."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.scanner.hunter import ScanTimeoutError, ToolCallback, run_hunter_scan
from app.scanner.parsers import (
    parse_amass_output,
    parse_dnsx_output,
    parse_ffuf_output,
    parse_httpx_output,
    parse_gobuster_output,
    parse_nikto_output,
    parse_nmap_output,
    parse_nuclei_output,
    parse_subfinder_output,
    parse_testssl_output,
    parse_tlsx_output,
    parse_whatweb_output,
    parse_wapiti_output,
)
from app.scanner.remote import run_hunter_scan_remote

log = logging.getLogger("orqelis.scanner")

SCAN_SEQUENCE = [
    {"tool": "subfinder", "timeout_s": 120},
    {"tool": "amass", "timeout_s": 120},
    {"tool": "dnsx", "timeout_s": 90, "stdin_from": "subfinder"},
    {"tool": "httpx", "timeout_s": 60, "stdin_from": "subfinder"},
    {"tool": "whatweb", "timeout_s": 90, "stdin_from": "httpx"},
    {"tool": "tlsx", "timeout_s": 90, "stdin_from": "httpx"},
    {"tool": "testssl.sh", "timeout_s": 240, "stdin_from": "httpx"},
    {"tool": "katana", "timeout_s": 120, "stdin_from": "httpx"},
    {"tool": "gobuster", "timeout_s": 90, "stdin_from": "katana"},
    {"tool": "ffuf", "timeout_s": 100, "stdin_from": "katana", "operator_enabled": True},
    {"tool": "nikto", "timeout_s": 90, "stdin_from": "katana"},
    {"tool": "wapiti", "timeout_s": 180, "stdin_from": "katana", "operator_enabled": True},
    {"tool": "nmap", "timeout_s": 180},
    {"tool": "nuclei", "timeout_s": 300, "stdin_from": "katana"},
]

__all__ = [
    "ScanTimeoutError",
    "execute_scan",
    "mock_scan",
    "normalize_raw",
    "run_hunter_scan",
    "run_hunter_scan_remote",
    "run_docker_scan",
]


def mock_scan(domain: str) -> dict[str, Any]:
    """Deterministic findings for tests and environments without scan tools."""
    subfinder = "\n".join(
        [
            domain,
            f"www.{domain}",
            f"api.{domain}",
            f"staging.{domain}",
            f"dev.{domain}",
            f"admin.{domain}",
        ]
    )
    httpx_out = "\n".join(
        [
            json.dumps({"url": f"https://{domain}", "status_code": 200, "tech": ["nginx"], "title": "Home"}),
            json.dumps({"url": f"https://staging.{domain}", "status_code": 503, "title": "Staging"}),
        ]
    )
    nuclei = "\n".join(
        [
            json.dumps(
                {
                    "template-id": "missing-csp",
                    "info": {
                        "name": "Missing Content-Security-Policy",
                        "description": "CSP header not present on primary origin.",
                        "severity": "medium",
                    },
                    "matched-at": f"https://{domain}",
                    "matcher-name": "header",
                }
            ),
            json.dumps(
                {
                    "template-id": "exposed-git",
                    "info": {
                        "name": "Exposed .git directory",
                        "description": "HTTP response indicates .git metadata may be reachable.",
                        "severity": "high",
                    },
                    "matched-at": f"https://dev.{domain}/.git/",
                    "matcher-name": "status",
                }
            ),
        ]
    )
    nmap = f"Host: {domain} () Ports: 80/open/tcp//http///, 443/open/tcp//https///, 22/open/tcp//ssh///"
    tlsx = json.dumps(
        {"host": f"staging.{domain}", "port": "443", "tls_version": "tls11", "self_signed": True, "subject_cn": f"staging.{domain}"}
    )
    katana = "\n".join([f"https://{domain}/", f"https://{domain}/login", f"https://{domain}/api/health"])
    gobuster = "https://example.com/login (Status: 200)\nhttps://example.com/admin (Status: 302)\n"
    nikto = '{"host":"https://example.com","results":[{"msg":"X-Frame-Options header missing"}]}\n'
    return {
        "tools_run": ["subfinder", "amass", "dnsx", "httpx", "whatweb", "tlsx", "testssl.sh", "katana", "gobuster", "nikto", "nmap", "nuclei"],
        "tools_skipped": [tool for tool, enabled in (("ffuf", settings.scanner_enable_ffuf), ("wapiti", settings.scanner_enable_wapiti)) if not enabled],
        "raw_output": {
            "subfinder": subfinder,
            "amass": f"{domain}\nwww.{domain}",
            "dnsx": f"{domain} [A] [203.0.113.10]",
            "httpx": httpx_out,
            "whatweb": f"https://{domain} [200 OK] HTTPServer[nginx]",
            "tlsx": tlsx,
            "testssl.sh": "TLS 1.3 offered (OK)",
            "katana": katana,
            "gobuster": gobuster,
            "nikto": nikto,
            "nmap": nmap,
            "nuclei": nuclei,
        },
        "errors": [],
        "status": "completed",
        "error_message": None,
    }


def normalize_raw(domain: str, raw_output: dict[str, str], preparsed: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if preparsed:
        return list(preparsed)
    findings: list[dict[str, Any]] = []
    findings.extend(parse_subfinder_output(raw_output.get("subfinder", ""), domain))
    findings.extend(parse_amass_output(raw_output.get("amass", ""), domain))
    findings.extend(parse_dnsx_output(raw_output.get("dnsx", "")))
    findings.extend(parse_httpx_output(raw_output.get("httpx", "")))
    findings.extend(parse_whatweb_output(raw_output.get("whatweb", "")))
    findings.extend(parse_tlsx_output(raw_output.get("tlsx", "")))
    findings.extend(parse_testssl_output(raw_output.get("testssl.sh", "")))
    findings.extend(parse_gobuster_output(raw_output.get("gobuster", "")))
    findings.extend(parse_ffuf_output(raw_output.get("ffuf", "")))
    findings.extend(parse_nikto_output(raw_output.get("nikto", "")))
    findings.extend(parse_wapiti_output(raw_output.get("wapiti", "")))
    findings.extend(parse_nmap_output(raw_output.get("nmap", ""), domain))
    findings.extend(parse_nuclei_output(raw_output.get("nuclei", "")))
    return findings


async def run_docker_scan(domain: str) -> dict[str, Any]:
    """Legacy path: disposable Kali scanner image (Full Merge Part 3)."""
    image = settings.scanner_docker_image
    if not shutil.which("docker"):
        raise RuntimeError("Docker is not available on this host")
    work = Path(tempfile.mkdtemp(prefix="orqelis-scan-"))
    try:
        out_dir = work / "out"
        out_dir.mkdir()
        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "bridge",
            "-e",
            f"TARGET_DOMAIN={domain}",
            "-v",
            f"{out_dir}:/scan/out",
            image,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=settings.scan_timeout_total_s)
        except asyncio.TimeoutError:
            proc.kill()
            raise ScanTimeoutError(f"Scan exceeded {settings.scan_timeout_total_s}s") from None
        result_file = out_dir / "result.json"
        if result_file.exists():
            data = json.loads(result_file.read_text(encoding="utf-8"))
            return data
        err = (stderr or stdout or b"").decode("utf-8", errors="replace")[:2000]
        return {
            "tools_run": [],
            "raw_output": {},
            "errors": [err],
            "status": "failed",
            "error_message": err or f"scanner exited {proc.returncode}",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def execute_scan(domain: str, on_tool: ToolCallback | None = None) -> dict[str, Any]:
    mode = (settings.scanner_mode or "local").lower()
    if mode == "mock":
        result = mock_scan(domain)
        for tool in result["tools_run"]:
            if on_tool:
                await on_tool(tool)
            if settings.scanner_mock_step_delay_s > 0:
                await asyncio.sleep(settings.scanner_mock_step_delay_s)
        return result
    # SSRF gate for any non-mock backend
    from app.domain_validation import domain_resolves_to_private

    if domain_resolves_to_private(domain):
        return {
            "tools_run": [],
            "raw_output": {},
            "errors": ["Domain resolves to a private or unresolvable address"],
            "status": "failed",
            "error_message": "Refusing to scan private/unresolvable domain",
        }
    if mode == "remote":
        return await run_hunter_scan_remote(domain)
    if mode == "docker":
        return await run_docker_scan(domain)
    # Option A default: in-process ProjectDiscovery tools
    return await run_hunter_scan(domain, on_tool=on_tool)

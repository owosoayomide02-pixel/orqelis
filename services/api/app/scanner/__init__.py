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
from app.scanner.hunter import ScanTimeoutError, run_hunter_scan
from app.scanner.parsers import (
    parse_httpx_output,
    parse_nmap_output,
    parse_nuclei_output,
    parse_subfinder_output,
)
from app.scanner.remote import run_hunter_scan_remote

log = logging.getLogger("orqelis.scanner")

SCAN_SEQUENCE = [
    {"tool": "subfinder", "timeout_s": 120},
    {"tool": "httpx", "timeout_s": 60, "stdin_from": "subfinder"},
    {"tool": "nuclei", "timeout_s": 300, "stdin_from": "httpx"},
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
    return {
        "tools_run": ["subfinder", "httpx", "nmap", "nuclei"],
        "raw_output": {"subfinder": subfinder, "httpx": httpx_out, "nmap": nmap, "nuclei": nuclei},
        "errors": [],
        "status": "completed",
        "error_message": None,
    }


def normalize_raw(domain: str, raw_output: dict[str, str], preparsed: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if preparsed:
        return list(preparsed)
    findings: list[dict[str, Any]] = []
    findings.extend(parse_subfinder_output(raw_output.get("subfinder", ""), domain))
    findings.extend(parse_httpx_output(raw_output.get("httpx", "")))
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


async def execute_scan(domain: str) -> dict[str, Any]:
    mode = (settings.scanner_mode or "local").lower()
    if mode == "mock":
        return mock_scan(domain)
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
    return await run_hunter_scan(domain)

"""Standalone Hunter scanner (Option B) — copy of API hunter logic, no cross-service imports."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import shutil
import socket
from typing import Any

log = logging.getLogger("orqelis.scanner_service")


class ScanTimeoutError(Exception):
    pass


def _is_private_ip(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _domain_resolves_private(domain: str) -> bool:
    try:
        infos = socket.getaddrinfo(domain, None)
    except OSError:
        return True
    if not infos:
        return True
    for info in infos:
        if _is_private_ip(info[4][0]):
            return True
    return False


def filter_public_hosts(hosts: list[str]) -> list[str]:
    public: list[str] = []
    for host in hosts:
        host = (host or "").strip().lower()
        if not host:
            continue
        try:
            ipaddress.ip_address(host)
            continue
        except ValueError:
            pass
        if _domain_resolves_private(host):
            continue
        public.append(host)
    return public


async def run_tool(cmd: list[str], timeout_s: int, stdin_data: str | None = None) -> str:
    if not cmd or not shutil.which(cmd[0]):
        raise FileNotFoundError(f"Tool not found on PATH: {cmd[0] if cmd else '?'}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if stdin_data is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_data.encode() if stdin_data is not None else None),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await proc.wait()
        except Exception:
            pass
        raise ScanTimeoutError(f"{cmd[0]} exceeded {timeout_s}s") from None
    out = (stdout or b"").decode("utf-8", errors="replace")
    if proc.returncode not in (0, None) and not out.strip():
        err = (stderr or b"").decode("utf-8", errors="replace")[:500]
        log.warning("%s exited %s: %s", cmd[0], proc.returncode, err)
    return out


def _hosts_from_subfinder_lines(raw: str, root_domain: str) -> list[str]:
    hosts: list[str] = []
    for line in (raw or "").splitlines():
        host = line.strip()
        if not host:
            continue
        if host.startswith("{"):
            try:
                data = json.loads(host)
                host = str(data.get("host") or data.get("input") or "")
            except Exception:
                continue
        if host and host not in hosts:
            hosts.append(host)
    if root_domain not in hosts:
        hosts.insert(0, root_domain)
    return hosts


def _urls_from_httpx(raw: str, domain: str) -> str:
    urls: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line.split()[0])
            continue
        try:
            data = json.loads(line)
            url = str(data.get("url") or "")
            if url:
                urls.append(url)
        except Exception:
            continue
    if not urls:
        urls = [f"https://{domain}"]
    return "\n".join(urls) + "\n"


def parse_nuclei_output(raw: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = data.get("info") or {}
        severity = str(info.get("severity") or "medium").lower()
        findings.append(
            {
                "title": str(info.get("name") or data.get("template-id") or "Nuclei finding")[:240],
                "description": str(info.get("description") or ""),
                "severity": severity,
                "tool_source": "nuclei",
                "raw_reference": {
                    "template_id": data.get("template-id"),
                    "matched_at": data.get("matched-at"),
                },
            }
        )
    return findings


async def run_hunter_scan(domain: str) -> dict[str, Any]:
    results: dict[str, Any] = {
        "tools_run": [],
        "raw_output": {},
        "errors": [],
        "status": "completed",
        "error_message": None,
    }

    subfinder_out = domain
    try:
        subfinder_out = await run_tool(["subfinder", "-d", domain, "-silent"], timeout_s=120)
        results["tools_run"].append("subfinder")
        results["raw_output"]["subfinder"] = subfinder_out
    except ScanTimeoutError as exc:
        results["errors"].append(str(exc))
        subfinder_out = domain
        results["raw_output"]["subfinder"] = domain
    except FileNotFoundError as exc:
        results["errors"].append(str(exc))
        results["status"] = "failed"
        results["error_message"] = str(exc)
        return results

    hosts = filter_public_hosts(_hosts_from_subfinder_lines(subfinder_out, domain))
    if not hosts:
        results["errors"].append("No public hosts remaining after SSRF filter")
        results["status"] = "failed"
        results["error_message"] = "No public hosts to scan"
        return results
    host_stdin = "\n".join(hosts) + "\n"
    safe_fallback_url = f"https://{domain}\n" if domain in hosts else f"https://{hosts[0]}\n"

    httpx_out = safe_fallback_url
    try:
        httpx_out = await run_tool(["httpx", "-silent", "-json"], timeout_s=60, stdin_data=host_stdin)
        results["tools_run"].append("httpx")
        results["raw_output"]["httpx"] = httpx_out
    except ScanTimeoutError as exc:
        results["errors"].append(str(exc))
        httpx_out = safe_fallback_url
        results["raw_output"]["httpx"] = httpx_out
    except FileNotFoundError as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["httpx"] = httpx_out

    nuclei_stdin = _urls_from_httpx(httpx_out, hosts[0])
    allowed = set(hosts)
    filtered_urls: list[str] = []
    for line in nuclei_stdin.splitlines():
        line = line.strip()
        if not line:
            continue
        host = line.split("://", 1)[-1].split("/", 1)[0].split(":")[0].lower()
        if host in allowed:
            filtered_urls.append(line)
    if not filtered_urls:
        results["errors"].append("No public URLs remaining for nuclei")
        results["status"] = "failed"
        results["error_message"] = "No public URLs to scan"
        return results
    nuclei_stdin = "\n".join(filtered_urls) + "\n"

    try:
        nmap_out = await run_tool(
            ["nmap", "-Pn", "-sT", "-sV", "--top-ports", "100", "-T4", "-oG", "-", domain],
            timeout_s=180,
        )
        results["tools_run"].append("nmap")
        results["raw_output"]["nmap"] = nmap_out
    except ScanTimeoutError as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["nmap"] = ""
    except FileNotFoundError as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["nmap"] = ""

    try:
        nuclei_out = await run_tool(
            ["nuclei", "-jsonl", "-severity", "low,medium,high,critical", "-silent"],
            timeout_s=300,
            stdin_data=nuclei_stdin,
        )
        results["tools_run"].append("nuclei")
        results["raw_output"]["nuclei"] = nuclei_out
    except ScanTimeoutError as exc:
        results["errors"].append(str(exc))
        results["status"] = "timed_out"
        results["error_message"] = str(exc)
    except FileNotFoundError as exc:
        results["errors"].append(str(exc))
        if results["status"] != "timed_out":
            results["status"] = "failed"
            results["error_message"] = str(exc)

    if results["errors"] and results["status"] == "completed" and "nuclei" not in results["tools_run"]:
        results["status"] = "failed"
        results["error_message"] = "; ".join(results["errors"])[:500]
    elif results["errors"] and results["status"] == "completed":
        results["error_message"] = "; ".join(results["errors"])[:500]

    return results

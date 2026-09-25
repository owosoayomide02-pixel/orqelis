"""In-process Hunter scan — ProjectDiscovery tools on the API host (Option A)."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

from app.domain_validation import filter_public_hosts

log = logging.getLogger("orqelis.scanner.hunter")


class ScanTimeoutError(Exception):
    pass


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
        # subfinder -silent prints one host per line; also accept JSON lines
        if host.startswith("{"):
            try:
                import json

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
            import json

            data = json.loads(line)
            url = str(data.get("url") or "")
            if url:
                urls.append(url)
        except Exception:
            continue
    if not urls:
        urls = [f"https://{domain}"]
    return "\n".join(urls) + "\n"


async def run_hunter_scan(domain: str) -> dict[str, Any]:
    """Run subfinder → httpx → nuclei against a verified public domain."""
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

    # SSRF: drop hosts that resolve private/link-local before probing
    hosts = filter_public_hosts(_hosts_from_subfinder_lines(subfinder_out, domain))
    if not hosts:
        results["errors"].append("No public hosts remaining after SSRF filter")
        results["status"] = "failed"
        results["error_message"] = "No public hosts to scan"
        return results
    host_stdin = "\n".join(hosts) + "\n"
    # Safe URL fallback only if the apex itself survived the public-host filter
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

    nuclei_stdin = _urls_from_httpx(httpx_out, hosts[0] if hosts else domain)
    # Drop any URL whose hostname did not pass the public filter
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

    # nmap service discovery (authorized surface only — no exploit scripts)
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
        # Partial success — keep completed, surface errors
        results["error_message"] = "; ".join(results["errors"])[:500]

    return results

"""In-process Hunter scan — ProjectDiscovery tools on the API host (Option A)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from app.config import settings
from app.domain_validation import filter_public_hosts
from app.scanner.parsers import urls_from_katana

log = logging.getLogger("orqelis.scanner.hunter")

ToolCallback = Callable[[str], Awaitable[None]]


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
        host = host.lower().rstrip(".")
        root = root_domain.lower().rstrip(".")
        if host and (host == root or host.endswith(f".{root}")) and host not in hosts:
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


async def run_hunter_scan(domain: str, on_tool: ToolCallback | None = None) -> dict[str, Any]:
    """Run subfinder → httpx → tlsx → katana → nmap → nuclei against a verified public domain."""
    results: dict[str, Any] = {
        "tools_run": [],
        "tools_skipped": [],
        "raw_output": {},
        "errors": [],
        "status": "completed",
        "error_message": None,
    }

    async def starting(tool: str) -> None:
        if on_tool:
            await on_tool(tool)

    subfinder_out = domain
    await starting("subfinder")
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

    await starting("amass")
    try:
        amass_out = await run_tool(["amass", "enum", "-passive", "-d", domain], timeout_s=120)
        results["tools_run"].append("amass")
        results["raw_output"]["amass"] = amass_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["amass"] = ""

    # SSRF: merge only root-domain discoveries, cap volume, then drop private hosts.
    discovered_hosts = _hosts_from_subfinder_lines(f"{subfinder_out}\n{results['raw_output']['amass']}", domain)
    hosts = filter_public_hosts(discovered_hosts[:100])
    if not hosts:
        results["errors"].append("No public hosts remaining after SSRF filter")
        results["status"] = "failed"
        results["error_message"] = "No public hosts to scan"
        return results
    host_stdin = "\n".join(hosts) + "\n"
    # Safe URL fallback only if the apex itself survived the public-host filter
    safe_fallback_url = f"https://{domain}\n" if domain in hosts else f"https://{hosts[0]}\n"

    # DNS record enrichment is limited to the already discovered, public host list.
    await starting("dnsx")
    try:
        dnsx_out = await run_tool(
            ["dnsx", "-silent", "-a", "-aaaa", "-cname", "-resp"],
            timeout_s=90,
            stdin_data=host_stdin,
        )
        results["tools_run"].append("dnsx")
        results["raw_output"]["dnsx"] = dnsx_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["dnsx"] = ""

    httpx_out = safe_fallback_url
    await starting("httpx")
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
    live_hosts = sorted({u.split("://", 1)[1].split("/", 1)[0].split(":")[0].lower() for u in filtered_urls})

    # Fingerprint only a bounded set of public, in-scope HTTP endpoints.
    await starting("whatweb")
    try:
        whatweb_out = await run_tool(
            ["whatweb", "--quiet", "--color=never", "--no-errors", *filtered_urls[:10]],
            timeout_s=90,
        )
        results["tools_run"].append("whatweb")
        results["raw_output"]["whatweb"] = whatweb_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["whatweb"] = ""

    # TLS certificate / protocol posture (read-only handshake)
    await starting("tlsx")
    try:
        tlsx_out = await run_tool(
            ["tlsx", "-silent", "-json", "-expired", "-self-signed", "-mismatched", "-revoked", "-tls-version"],
            timeout_s=90,
            stdin_data="\n".join(live_hosts) + "\n",
        )
        results["tools_run"].append("tlsx")
        results["raw_output"]["tlsx"] = tlsx_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["tlsx"] = ""

    # Deeper TLS checks are read-only and restricted to the public HTTP host set.
    await starting("testssl.sh")
    try:
        testssl_out = await run_tool(
            ["testssl.sh", "--quiet", "--warnings", "off", "--color", "0", "--fast", *live_hosts[:10]],
            timeout_s=240,
        )
        results["tools_run"].append("testssl.sh")
        results["raw_output"]["testssl.sh"] = testssl_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["testssl.sh"] = ""

    # Crawl live sites so nuclei covers discovered pages, not just each homepage
    await starting("katana")
    try:
        katana_out = await run_tool(
            ["katana", "-silent", "-d", "2", "-jc", "-ct", "90", "-rl", "30", "-fs", "rdn"],
            timeout_s=120,
            stdin_data="\n".join(filtered_urls) + "\n",
        )
        results["tools_run"].append("katana")
        results["raw_output"]["katana"] = katana_out
        for url in urls_from_katana(katana_out, allowed):
            if url not in filtered_urls:
                filtered_urls.append(url)
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["katana"] = ""
    nuclei_stdin = "\n".join(filtered_urls) + "\n"

    # Additional read-only directory and web app checks that match the approved Kali toolset.
    gobuster_wordlists = (
        "/usr/share/seclists/Discovery/Web-Content/common.txt",
        "/usr/share/dirb/wordlists/common.txt",
        "/usr/share/wordlists/dirb/common.txt",
    )
    gobuster_wordlist = next((path for path in gobuster_wordlists if os.path.isfile(path)), None)
    await starting("gobuster")
    try:
        if not gobuster_wordlist:
            raise FileNotFoundError("No gobuster wordlist found")
        gobuster_out = await run_tool(
            ["gobuster", "dir", "-u", filtered_urls[0], "-w", gobuster_wordlist, "-q", "-z", "-t", "5"],
            timeout_s=90,
        )
        results["tools_run"].append("gobuster")
        results["raw_output"]["gobuster"] = gobuster_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["gobuster"] = ""

    if settings.scanner_enable_ffuf:
        await starting("ffuf")
        try:
            if not gobuster_wordlist:
                raise FileNotFoundError("No SecLists web-content wordlist found")
            parsed_target = urlsplit(filtered_urls[0])
            ffuf_url = f"{parsed_target.scheme}://{parsed_target.netloc}/FUZZ"
            ffuf_out = await run_tool(
                [
                    "ffuf", "-noninteractive", "-s", "-u", ffuf_url, "-w", gobuster_wordlist,
                    "-rate", "5", "-t", "5", "-maxtime", "90", "-of", "json", "-o", "/dev/stdout",
                ],
                timeout_s=100,
            )
            results["tools_run"].append("ffuf")
            results["raw_output"]["ffuf"] = ffuf_out
        except (ScanTimeoutError, FileNotFoundError) as exc:
            results["errors"].append(str(exc))
            results["raw_output"]["ffuf"] = ""
    else:
        results["tools_skipped"].append("ffuf")
        results["raw_output"]["ffuf"] = "operator-disabled"

    await starting("nikto")
    try:
        parsed = urlsplit(filtered_urls[0])
        nikto_target = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else filtered_urls[0]
        nikto_out = await run_tool(
            ["nikto", "-h", nikto_target, "-Format", "json", "-Tuning", "1,2,3,4,5,6,7,8,9,10"],
            timeout_s=90,
        )
        results["tools_run"].append("nikto")
        results["raw_output"]["nikto"] = nikto_out
    except (ScanTimeoutError, FileNotFoundError) as exc:
        results["errors"].append(str(exc))
        results["raw_output"]["nikto"] = ""

    if settings.scanner_enable_wapiti:
        await starting("wapiti")
        try:
            parsed_target = urlsplit(filtered_urls[0])
            wapiti_url = f"{parsed_target.scheme}://{parsed_target.netloc}/"
            wapiti_out = await run_tool(
                ["wapiti", "-u", wapiti_url, "-f", "json", "-o", "/dev/stdout", "-d", "1"],
                timeout_s=180,
            )
            results["tools_run"].append("wapiti")
            results["raw_output"]["wapiti"] = wapiti_out
        except (ScanTimeoutError, FileNotFoundError) as exc:
            results["errors"].append(str(exc))
            results["raw_output"]["wapiti"] = ""
    else:
        results["tools_skipped"].append("wapiti")
        results["raw_output"]["wapiti"] = "operator-disabled"

    # nmap service discovery (authorized surface only — no exploit scripts)
    await starting("nmap")
    try:
        nmap_out = await run_tool(
            ["nmap", "-Pn", "-sT", "-sV", "--top-ports", "100", "-T4", "-oG", "-", *hosts],
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

    await starting("nuclei")
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

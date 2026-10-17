"""Normalize Hunter tool output into a shared finding shape."""

from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict


class NormalizedFinding(TypedDict):
    title: str
    description: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    tool_source: str
    raw_reference: dict[str, Any]
    evidence: str | None


def _trim_ref(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, str) and len(value) > 400:
                value = value[:400] + "…"
            out[key] = value
    return out


def parse_nuclei_line(line: str) -> NormalizedFinding | None:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    info = data.get("info") or {}
    severity = str(info.get("severity") or "medium").lower()
    if severity not in {"info", "low", "medium", "high", "critical"}:
        severity = "medium"
    return NormalizedFinding(
        title=str(info.get("name") or data.get("template-id") or "Nuclei finding")[:240],
        description=str(info.get("description") or ""),
        severity=severity,  # type: ignore[arg-type]
        tool_source="nuclei",
        raw_reference=_trim_ref(
            data,
            ["template-id", "matched-at", "host", "type"],
        ),
        evidence=str(data.get("matcher-name") or data.get("extracted-results") or "")[:500] or None,
    )


def parse_nuclei_output(raw: str) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        item = parse_nuclei_line(line)
        if item:
            findings.append(item)
    return findings


def parse_httpx_output(raw: str) -> list[NormalizedFinding]:
    """Only emit findings for notable signals (outdated/tech exposure), not every host."""
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = data.get("status_code") or data.get("status-code")
        tech = data.get("tech") or data.get("technologies") or []
        title_bits = []
        severity: Literal["info", "low", "medium", "high", "critical"] = "info"
        if status and int(status) >= 500:
            title_bits.append(f"HTTP {status}")
            severity = "medium"
        if tech:
            title_bits.append("Exposed technologies: " + ", ".join(str(t) for t in tech[:5]))
            if severity == "info":
                severity = "low"
        # Skip boring 200s with no tech
        if not title_bits:
            continue
        url = str(data.get("url") or data.get("input") or "host")
        findings.append(
            NormalizedFinding(
                title=f"{url}: {'; '.join(title_bits)}"[:240],
                description="httpx probe noted potentially interesting response metadata.",
                severity=severity,
                tool_source="httpx",
                raw_reference=_trim_ref(data, ["url", "status_code", "status-code", "title", "webserver"]),
                evidence=None,
            )
        )
    return findings


def parse_dnsx_output(raw: str) -> list[NormalizedFinding]:
    """Record DNS answers as informational inventory observations."""
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        match = re.match(r"^(\S+)\s+((?:\[[^\]]+\]\s*)+)$", line)
        if not match:
            continue
        host, answers = match.groups()
        records = re.findall(r"\[([^\]]+)\]", answers)
        if not records:
            continue
        findings.append(
            NormalizedFinding(
                title=f"DNS records identified for {host}"[:240],
                description="dnsx returned DNS records for this discovered, public host. This is inventory data, not a vulnerability determination.",
                severity="info",
                tool_source="dnsx",
                raw_reference={"host": host[:253], "records": records[:12]},
                evidence=line[:500],
            )
        )
    return findings


def parse_whatweb_output(raw: str) -> list[NormalizedFinding]:
    """Record WhatWeb fingerprints as informational observations, not vulnerabilities."""
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        match = re.match(r"^(https?://\S+)\s+(.+)$", line)
        if not match:
            continue
        url, fingerprint = match.groups()
        plugins = re.findall(r"([A-Za-z][A-Za-z0-9_-]*)\[([^\]]{1,160})\]", fingerprint)
        if not plugins:
            continue
        findings.append(
            NormalizedFinding(
                title=f"Technology fingerprint observed on {url}"[:240],
                description="WhatWeb identified HTTP response technologies. Verify versions and exposure independently; a fingerprint alone is not a vulnerability.",
                severity="info",
                tool_source="whatweb",
                raw_reference={"url": url[:400], "plugins": [{"name": name, "value": value} for name, value in plugins[:12]]},
                evidence=line[:500],
            )
        )
    return findings


def parse_amass_output(raw: str, root_domain: str) -> list[NormalizedFinding]:
    """Summarize passive Amass discoveries that belong to the registered root."""
    root = root_domain.lower().rstrip(".")
    hosts = sorted(
        {
            line.strip().lower().rstrip(".")
            for line in (raw or "").splitlines()
            if line.strip()
            and (line.strip().lower().rstrip(".") == root or line.strip().lower().rstrip(".").endswith(f".{root}"))
        }
    )
    if not hosts:
        return []
    return [
        NormalizedFinding(
            title=f"Passive Amass discovered {len(hosts)} hosts for {root}"[:240],
            description="Passive subdomain intelligence for the registered root domain. Validate ownership and scope before any further testing.",
            severity="info",
            tool_source="amass",
            raw_reference={"root_domain": root, "count": len(hosts), "sample": hosts[:20]},
            evidence=None,
        )
    ]


def parse_testssl_output(raw: str) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        text = line.strip()
        weak = re.search(r"TLS\s+1\.[01].*(?:offered|deprecated|VULNERABLE)", text, re.IGNORECASE)
        if weak:
            findings.append(
                NormalizedFinding(
                    title=f"Deprecated TLS protocol reported: {text[:180]}",
                    description="testssl.sh reported TLS 1.0 or TLS 1.1 as offered. Confirm against the service configuration; newer TLS versions are recommended.",
                    severity="medium",
                    tool_source="testssl.sh",
                    raw_reference={"line": text[:400]},
                    evidence=text[:500],
                )
            )
    return findings


def parse_ffuf_output(raw: str) -> list[NormalizedFinding]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return []
    findings: list[NormalizedFinding] = []
    for row in data.get("results", []) if isinstance(data, dict) else []:
        if not isinstance(row, dict):
            continue
        input_data = row.get("input") if isinstance(row.get("input"), dict) else {}
        url = str(row.get("url") or input_data.get("FUZZ") or "").strip()
        status = row.get("status")
        if not url:
            continue
        findings.append(
            NormalizedFinding(
                title=f"Ffuf discovered web path: {url}"[:240],
                description="A bounded directory discovery request received a matching HTTP response. Review the path manually; discovery alone is not a vulnerability.",
                severity="info",
                tool_source="ffuf",
                raw_reference={"url": url[:400], "status": status, "length": row.get("length")},
                evidence=None,
            )
        )
    return findings


def parse_wapiti_output(raw: str) -> list[NormalizedFinding]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return []
    vulnerabilities = data.get("vulnerabilities", {}) if isinstance(data, dict) else {}
    findings: list[NormalizedFinding] = []
    if isinstance(vulnerabilities, dict):
        rows = [(str(category), row) for category, values in vulnerabilities.items() if isinstance(values, list) for row in values]
    elif isinstance(vulnerabilities, list):
        rows = [("Wapiti finding", row) for row in vulnerabilities]
    else:
        rows = []
    for category, row in rows:
        if not isinstance(row, dict):
            continue
        level = str(row.get("level") or row.get("severity") or "").lower()
        severity = {"1": "low", "2": "medium", "3": "high", "4": "critical"}.get(level, level)
        if severity not in {"info", "low", "medium", "high", "critical"}:
            severity = "low"
        path = str(row.get("path") or row.get("url") or "")
        info = str(row.get("info") or row.get("description") or category)
        findings.append(
            NormalizedFinding(
                title=f"Wapiti: {category}"[:240],
                description=info[:1000],
                severity=severity,  # type: ignore[arg-type]
                tool_source="wapiti",
                raw_reference=_trim_ref(row, ["path", "url", "method", "level", "parameter"]),
                evidence=path[:500] or None,
            )
        )
    return findings


def parse_nmap_output(raw: str, domain: str) -> list[NormalizedFinding]:
    """Surface notable open ports/services from nmap text or greppable output."""
    findings: list[NormalizedFinding] = []
    interesting = {"21", "22", "23", "25", "110", "135", "139", "143", "445", "1433", "1521", "3306", "3389", "5432", "5900", "6379", "27017"}
    open_ports: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        # greppable: Host: x () Ports: 80/open/tcp//http///, 443/open/tcp//https///
        if "Ports:" in line:
            part = line.split("Ports:", 1)[1]
            for spec in part.split(","):
                spec = spec.strip()
                if "/open/" in spec:
                    port = spec.split("/", 1)[0].strip()
                    open_ports.append(spec.replace("//", "/"))
                    if port in interesting:
                        findings.append(
                            NormalizedFinding(
                                title=f"Open service on {domain}:{port}",
                                description=f"nmap reported an open port that often warrants review: {spec}",
                                severity="medium" if port in {"22", "3389", "445", "3306", "5432"} else "low",
                                tool_source="nmap",
                                raw_reference={"port_spec": spec[:200], "domain": domain},
                                evidence=spec[:300],
                            )
                        )
            continue
        # normal: 22/tcp open ssh
        if "/tcp" in line and " open " in line:
            bits = line.split()
            if bits:
                open_ports.append(line)
                port = bits[0].split("/")[0]
                if port in interesting or "ssl" in line.lower() or "http" in line.lower():
                    sev: Literal["info", "low", "medium", "high", "critical"] = (
                        "medium" if port in interesting else "info"
                    )
                    findings.append(
                        NormalizedFinding(
                            title=f"Open port on {domain}: {bits[0]}",
                            description=" ".join(bits[1:])[:400],
                            severity=sev,
                            tool_source="nmap",
                            raw_reference={"line": line[:200]},
                            evidence=line[:300],
                        )
                    )
    if len(open_ports) >= 8 and not findings:
        findings.append(
            NormalizedFinding(
                title=f"Broad open-port surface on {domain}",
                description=f"nmap found {len(open_ports)} open ports. Review unnecessary exposure.",
                severity="low",
                tool_source="nmap",
                raw_reference={"count": len(open_ports), "sample": open_ports[:12]},
                evidence=None,
            )
        )
    return findings


WEAK_TLS_VERSIONS = {"ssl30", "tls10", "tls11"}


def parse_tlsx_output(raw: str) -> list[NormalizedFinding]:
    """Certificate and protocol problems from `tlsx -json` (one JSON object per host:port)."""
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        target = f"{data.get('host') or data.get('ip') or 'host'}:{data.get('port') or 443}"
        ref = _trim_ref(data, ["host", "port", "tls_version", "subject_cn", "issuer_cn", "not_after"])
        checks: list[tuple[bool, str, str, Literal["low", "medium", "high"]]] = [
            (bool(data.get("expired")), "Expired TLS certificate", "Browsers will warn visitors and block API clients.", "high"),
            (bool(data.get("revoked")), "Revoked TLS certificate", "The issuing CA has revoked this certificate.", "high"),
            (bool(data.get("self_signed")), "Self-signed TLS certificate", "Not trusted by browsers; enables interception warnings to be ignored.", "medium"),
            (bool(data.get("mismatched")), "TLS certificate hostname mismatch", "The certificate does not cover this hostname.", "medium"),
            (
                str(data.get("tls_version") or "").lower() in WEAK_TLS_VERSIONS,
                f"Deprecated TLS protocol ({data.get('tls_version')})",
                "TLS 1.0/1.1 and SSLv3 are deprecated; require TLS 1.2 or newer.",
                "medium",
            ),
        ]
        for hit, title, description, severity in checks:
            if hit:
                findings.append(
                    NormalizedFinding(
                        title=f"{title} on {target}"[:240],
                        description=description,
                        severity=severity,
                        tool_source="tlsx",
                        raw_reference=ref,
                        evidence=None,
                    )
                )
    return findings


def parse_gobuster_output(raw: str) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        match = re.search(r"^(.*?)\s+\(Status:\s*(\d{3})\)", line)
        if not match:
            continue
        path, status = match.groups()
        findings.append(
            NormalizedFinding(
                title=f"Discovered web path: {path}"[:240],
                description=f"Gobuster found a web path responding with HTTP {status}.",
                severity="low",
                tool_source="gobuster",
                raw_reference={"path": path[:400], "status_code": int(status)},
                evidence=line[:500],
            )
        )
    return findings


def parse_nikto_output(raw: str) -> list[NormalizedFinding]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = []
        for line in raw.splitlines():
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    entries: list[dict[str, Any]] = []
    objects = data if isinstance(data, list) else [data]
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        for key in ("vulnerabilities", "results", "findings"):
            values = obj.get(key)
            if isinstance(values, list):
                entries.extend(item for item in values if isinstance(item, dict))
        if any(obj.get(key) for key in ("msg", "message", "description")):
            entries.append(obj)

    findings: list[NormalizedFinding] = []
    for entry in entries:
        message = str(entry.get("msg") or entry.get("message") or entry.get("description") or "").strip()
        if not message:
            continue
        severity = str(entry.get("severity") or "low").lower()
        if severity not in {"info", "low", "medium", "high", "critical"}:
            severity = "low"
        findings.append(
            NormalizedFinding(
                title=f"Nikto: {message}"[:240],
                description=message[:1000],
                severity=severity,  # type: ignore[arg-type]
                tool_source="nikto",
                raw_reference=_trim_ref(entry, ["id", "OSVDB", "url", "method", "severity"]),
                evidence=message[:500],
            )
        )
    return findings


def urls_from_katana(raw: str, allowed_hosts: set[str], limit: int = 150) -> list[str]:
    """Crawled URLs (plain lines or JSONL) restricted to hosts that passed the public-host filter."""
    urls: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            line = str((data.get("request") or {}).get("endpoint") or data.get("endpoint") or data.get("url") or "")
        if not line.startswith(("http://", "https://")):
            continue
        host = line.split("://", 1)[1].split("/", 1)[0].split(":")[0].lower()
        if host in allowed_hosts and line not in urls:
            urls.append(line)
        if len(urls) >= limit:
            break
    return urls


def parse_subfinder_output(raw: str, root_domain: str) -> list[NormalizedFinding]:
    """Subfinder feeds httpx; only flag unexpected volume as a soft finding."""
    hosts: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            host = str(data.get("host") or data.get("input") or "")
        except json.JSONDecodeError:
            host = line
        if host and host not in hosts:
            hosts.append(host)
    if len(hosts) < 5:
        return []
    return [
        NormalizedFinding(
            title=f"Large subdomain surface on {root_domain}",
            description=f"Discovered {len(hosts)} subdomains. Review for unexpected exposure.",
            severity="info",
            tool_source="subfinder",
            raw_reference={"count": len(hosts), "sample": hosts[:10]},
            evidence=None,
        )
    ]


def hosts_from_subfinder(raw: str, root_domain: str) -> list[str]:
    hosts: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            host = str(data.get("host") or data.get("input") or "")
        except json.JSONDecodeError:
            host = line
        if host and host not in hosts:
            hosts.append(host)
    if root_domain not in hosts:
        hosts.insert(0, root_domain)
    return hosts

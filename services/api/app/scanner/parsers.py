"""Normalize Hunter tool output into a shared finding shape."""

from __future__ import annotations

import json
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

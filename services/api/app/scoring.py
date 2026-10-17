from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import Alert, Device, Incident, Vulnerability

ONLINE_WINDOW = timedelta(minutes=2)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def is_online(device: Device, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    last = _aware(device.last_seen_at)
    return bool(last and now - last < ONLINE_WINDOW and device.status != "revoked")


def posture_checklist(device: Device, *, high_open_alerts: int, now: datetime | None = None) -> list[dict[str, Any]]:
    health = device.health_json or {}
    posture = device.posture_json or {}
    defender = str(posture.get("defender_status") or "").lower()
    firewall = str(posture.get("firewall_status") or "").lower()
    online = is_online(device, now)
    return [
        {
            "id": "agent_online",
            "label": "Agent online",
            "ok": online,
            "detail": "Last seen within two minutes" if online else "Agent has not checked in recently",
        },
        {
            "id": "defender",
            "label": "Endpoint protection reported on",
            "ok": defender != "off",
            "skip": defender not in {"on", "off"},
            "detail": f"Status: {defender or 'unknown'}",
        },
        {
            "id": "firewall",
            "label": "Host firewall reported on",
            "ok": firewall != "off",
            "skip": firewall not in {"on", "off"},
            "detail": f"Status: {firewall or 'unknown'}",
        },
        {
            "id": "security_log",
            "label": "Security / auth log readable",
            "ok": bool(health.get("can_read_security_log")),
            "detail": "Required for authentication detections",
        },
        {
            "id": "no_high_alerts",
            "label": "No open High or Critical alerts",
            "ok": high_open_alerts == 0,
            "detail": f"{high_open_alerts} open high-impact alert(s)" if high_open_alerts else "None open",
        },
    ]


def compute_score(
    *,
    devices: list[Device],
    alerts: list[Alert],
    incidents: list[Incident],
    vulnerabilities: list[Vulnerability],
    now: datetime | None = None,
) -> dict[str, Any]:
    active_devices = [d for d in devices if d.revoked_at is None]
    open_alerts = [a for a in alerts if a.status == "open"]
    open_incidents = [i for i in incidents if i.status in {"open", "investigating"}]
    open_vulns = [v for v in vulnerabilities if v.status == "open"]

    if not active_devices and not open_alerts and not open_incidents and not open_vulns:
        return {
            "score": None,
            "first_run": True,
            "summary": "Add a domain or web asset to start external security scanning.",
            "drivers": [],
            "counts": {"devices": 0, "alerts_open": 0, "incidents_open": 0, "vulnerabilities_open": 0},
        }

    score = 100
    drivers: list[dict[str, Any]] = []

    def penalize(points: int, reason: str, fix: str) -> None:
        nonlocal score
        score -= points
        drivers.append({"reason": reason, "impact": -points, "fix": fix})

    offline = [d for d in active_devices if not is_online(d, now)]
    if offline:
        points = min(36, 12 * len(offline))
        penalize(points, f"{len(offline)} device(s) offline", "Start the Orqelis agent on each enrolled computer.")

    for device in active_devices:
        posture = device.posture_json or {}
        health = device.health_json or {}
        name = device.hostname or device.name or device.id[:8]
        if str(posture.get("defender_status") or "").lower() == "off":
            penalize(20, f"Endpoint protection off on {name}", "Re-enable Defender, Gatekeeper, or the host malware protection control.")
        if str(posture.get("firewall_status") or "").lower() == "off":
            penalize(15, f"Firewall off on {name}", "Re-enable the host firewall profiles.")
        if health.get("can_read_security_log") is False:
            penalize(8, f"Limited telemetry on {name}", "Run the agent with permission to read security/auth logs.")

    open_alerts = [a for a in alerts if a.status == "open"]
    critical = [a for a in open_alerts if a.severity == "critical"]
    high = [a for a in open_alerts if a.severity == "high"]
    if critical:
        penalize(min(36, 18 * len(critical)), f"{len(critical)} open Critical alert(s)", "Investigate Critical alerts and confirm or resolve them.")
    if high:
        penalize(min(30, 10 * len(high)), f"{len(high)} open High alert(s)", "Triage High alerts on the Alerts page.")

    open_incidents = [i for i in incidents if i.status in {"open", "investigating"}]
    if open_incidents:
        penalize(min(24, 8 * len(open_incidents)), f"{len(open_incidents)} open incident(s)", "Assign an owner and update incident status.")

    open_vulns = [v for v in vulnerabilities if v.status == "open"]
    if open_vulns:
        penalize(min(24, 6 * len(open_vulns)), f"{len(open_vulns)} open posture finding(s)", "Restore disabled security controls on affected devices.")

    score = max(0, min(100, score))
    drivers.sort(key=lambda item: item["impact"])
    return {
        "score": score,
        "first_run": False,
        "summary": "Calculated from this organization's devices, open alerts, incidents, and posture findings only.",
        "drivers": drivers[:5],
        "counts": {
            "devices": len(active_devices),
            "alerts_open": len(open_alerts),
            "incidents_open": len(open_incidents),
            "vulnerabilities_open": len(open_vulns),
        },
    }


WEB_EXTRA_WEIGHT = {"critical": 5, "high": 3, "medium": 1, "low": 0}


def compute_web_risk(*, alerts: list[Alert], scanned: bool) -> dict[str, Any]:
    """Exposure risk for a web asset: 0 (clean) to 100 (severe). None until a scan has completed.

    The worst open finding sets the floor; each additional finding adds a small, severity-weighted bump.
    """
    open_alerts = [a for a in alerts if a.status == "open"]
    by_severity = {sev: sum(1 for a in open_alerts if a.severity == sev) for sev in ("critical", "high", "medium", "low")}
    if not scanned:
        return {"risk_score": None, "open_findings": len(open_alerts), "by_severity": by_severity}
    if not open_alerts:
        return {"risk_score": 0, "open_findings": 0, "by_severity": by_severity}
    ranked = sorted(open_alerts, key=lambda a: a.risk_score or 0, reverse=True)
    score = ranked[0].risk_score or 0
    score += sum(WEB_EXTRA_WEIGHT.get(a.severity, 0) for a in ranked[1:])
    return {"risk_score": max(0, min(100, score)), "open_findings": len(open_alerts), "by_severity": by_severity}

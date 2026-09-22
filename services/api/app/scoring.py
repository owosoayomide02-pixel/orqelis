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
    now = now or datetime.now(UTC)
    active_devices = [d for d in devices if d.revoked_at is None]
    if not active_devices:
        return {
            "score": None,
            "first_run": True,
            "summary": "Enroll an authorized device before Orqelis can calculate a security score.",
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

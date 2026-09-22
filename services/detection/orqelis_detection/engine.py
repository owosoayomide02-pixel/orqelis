from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class DetectionFinding:
    rule_id: str
    title: str
    severity: str
    confidence: float
    risk_score: int
    recommended_next_step: str
    evidence: dict[str, Any]
    event_ids: list[str] = field(default_factory=list)
    device_id: str | None = None
    finding_type: str = "alert"  # alert | vulnerability


class BaselineProvider(Protocol):
    def is_unusual(self, device_id: str, category: str, value: Any) -> bool: ...


class AnomalyModel(Protocol):
    def score(self, events: list[dict[str, Any]]) -> float: ...


class ThreatIntelProvider(Protocol):
    def match(self, indicator: str) -> dict[str, Any] | None: ...


class NullBaseline:
    def is_unusual(self, device_id: str, category: str, value: Any) -> bool:
        return False


class NullAnomaly:
    def score(self, events: list[dict[str, Any]]) -> float:
        return 0.0


class NullThreatIntel:
    def match(self, indicator: str) -> dict[str, Any] | None:
        return None


SUSPICIOUS_PROCESS_MARKERS = (
    " -enc ",
    " -encodedcommand ",
    "frombase64string",
    "iex(",
    "invoke-expression",
    "downloadstring",
    "bypass",
    "regsvr32",
    "mshta",
    "wscript.shell",
)

TEMP_PATH_MARKERS = ("\\temp\\", "\\appdata\\local\\temp\\", "/tmp/")


def _dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


class DetectionEngine:
    """Deterministic detection. LLMs are not used here."""

    def __init__(
        self,
        *,
        baseline: BaselineProvider | None = None,
        anomaly: AnomalyModel | None = None,
        threat_intel: ThreatIntelProvider | None = None,
    ) -> None:
        self.baseline = baseline or NullBaseline()
        self.anomaly = anomaly or NullAnomaly()
        self.threat_intel = threat_intel or NullThreatIntel()

    def analyze(self, events: Iterable[dict[str, Any]]) -> list[DetectionFinding]:
        items = list(events)
        findings: list[DetectionFinding] = []
        findings.extend(self._auth_failures(items))
        findings.extend(self._fail_then_success(items))
        findings.extend(self._privileged_account(items))
        findings.extend(self._security_control_changes(items))
        findings.extend(self._suspicious_processes(items))
        findings.extend(self._unusual_outbound(items))
        findings.extend(self._posture(items))
        return findings

    def correlate(self, findings: list[DetectionFinding]) -> list[dict[str, Any]]:
        """Group related findings on the same device into incidents."""
        by_device: dict[str, list[DetectionFinding]] = {}
        for finding in findings:
            key = finding.device_id or "unknown"
            by_device.setdefault(key, []).append(finding)
        incidents: list[dict[str, Any]] = []
        for device_id, group in by_device.items():
            rule_ids = {item.rule_id for item in group}
            high_value = {"auth_fail_burst", "auth_fail_then_success", "privileged_account_created", "suspicious_process", "unusual_outbound"}
            if len(rule_ids & high_value) >= 2:
                severity = "critical" if any(item.severity == "critical" for item in group) else "high"
                incidents.append(
                    {
                        "device_id": device_id if device_id != "unknown" else None,
                        "title": "Correlated suspicious activity on endpoint",
                        "summary": "Multiple related detections fired on the same device within this batch.",
                        "severity": severity,
                        "risk_score": min(100, max(item.risk_score for item in group) + 15 * (len(group) - 1)),
                        "findings": group,
                    }
                )
            elif any(item.severity in {"high", "critical"} for item in group):
                top = max(group, key=lambda item: item.risk_score)
                incidents.append(
                    {
                        "device_id": device_id if device_id != "unknown" else None,
                        "title": top.title,
                        "summary": top.recommended_next_step,
                        "severity": top.severity,
                        "risk_score": top.risk_score,
                        "findings": [top],
                    }
                )
        return incidents

    def _auth_failures(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        failures = [e for e in events if e.get("event_type") in {"4625", "auth_failure"}]
        if len(failures) < 5:
            return []
        device_id = failures[0].get("device_id")
        return [
            DetectionFinding(
                rule_id="auth_fail_burst",
                title="Repeated authentication failures",
                severity="medium",
                confidence=0.8,
                risk_score=45,
                recommended_next_step="Review the targeted account, source, and lockout policy. Reset credentials if compromise is suspected.",
                evidence={"count": len(failures), "sample": failures[:5]},
                event_ids=[str(e.get("id") or "") for e in failures if e.get("id")],
                device_id=device_id,
            )
        ]

    def _fail_then_success(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        ordered = sorted(events, key=lambda e: str(e.get("occurred_at") or ""))
        saw_fail = False
        success = None
        fails: list[dict[str, Any]] = []
        for event in ordered:
            if event.get("event_type") in {"4625", "auth_failure"}:
                saw_fail = True
                fails.append(event)
            elif saw_fail and event.get("event_type") in {"4624", "auth_success"}:
                success = event
                break
        if not success or len(fails) < 3:
            return []
        return [
            DetectionFinding(
                rule_id="auth_fail_then_success",
                title="Failed logons followed by a successful logon",
                severity="high",
                confidence=0.74,
                risk_score=72,
                recommended_next_step="Investigate the successful session, confirm the user, and consider resetting the credential.",
                evidence={"failures": len(fails), "success": success},
                event_ids=[str(e.get("id") or "") for e in fails + [success] if e.get("id")],
                device_id=success.get("device_id"),
            )
        ]

    def _privileged_account(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        created = [e for e in events if e.get("event_type") in {"4720", "privileged_account_created", "4672"}]
        out: list[DetectionFinding] = []
        for event in created:
            privileged = event.get("event_type") == "4672"
            out.append(
                DetectionFinding(
                    rule_id="privileged_account_created" if event.get("event_type") == "4720" else "privileged_logon",
                    title="Privileged account activity" if privileged else "New user account created",
                    severity="high",
                    confidence=0.7,
                    risk_score=68 if privileged else 60,
                    recommended_next_step="Confirm the change was authorized and review group membership.",
                    evidence={"event": event},
                    event_ids=[str(event.get("id") or "")] if event.get("id") else [],
                    device_id=event.get("device_id"),
                )
            )
        return out

    def _security_control_changes(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        findings: list[DetectionFinding] = []
        for event in events:
            if event.get("category") != "security_control":
                continue
            payload = event.get("payload") or event.get("payload_json") or {}
            platform = str(payload.get("platform") or "").lower()
            defender = str(payload.get("defender_status") or payload.get("defender") or "").lower()
            firewall = str(payload.get("firewall_status") or payload.get("firewall") or "").lower()
            if defender in {"off", "disabled", "false"} and platform not in {"linux"}:
                if platform == "darwin":
                    title = "macOS Gatekeeper reported disabled"
                    next_step = "Re-enable Gatekeeper (spctl) and investigate who changed the control."
                else:
                    title = "Microsoft Defender reported disabled"
                    next_step = "Re-enable Defender and investigate who changed the control."
                findings.append(
                    DetectionFinding(
                        rule_id="defender_disabled",
                        title=title,
                        severity="critical",
                        confidence=0.9,
                        risk_score=88,
                        recommended_next_step=next_step,
                        evidence={"payload": payload},
                        event_ids=[str(event.get("id") or "")] if event.get("id") else [],
                        device_id=event.get("device_id"),
                        finding_type="vulnerability",
                    )
                )
            if firewall in {"off", "disabled", "false"}:
                if platform == "darwin":
                    title = "macOS Application Firewall reported disabled"
                    next_step = "Re-enable socketfilterfw and review local security settings."
                elif platform == "linux":
                    title = "Linux host firewall reported inactive"
                    next_step = "Enable ufw or firewalld and review who changed the host firewall."
                else:
                    title = "Windows Firewall reported disabled"
                    next_step = "Re-enable the firewall profiles and review local policy changes."
                findings.append(
                    DetectionFinding(
                        rule_id="firewall_disabled",
                        title=title,
                        severity="high",
                        confidence=0.88,
                        risk_score=80,
                        recommended_next_step=next_step,
                        evidence={"payload": payload},
                        event_ids=[str(event.get("id") or "")] if event.get("id") else [],
                        device_id=event.get("device_id"),
                        finding_type="vulnerability",
                    )
                )
        return findings

    def _suspicious_processes(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        findings: list[DetectionFinding] = []
        for event in events:
            if event.get("category") != "process":
                continue
            payload = event.get("payload") or event.get("payload_json") or {}
            cmdline = str(payload.get("cmdline") or payload.get("command_line") or "").lower()
            path = str(payload.get("path") or payload.get("exe") or "").lower()
            blob = f"{cmdline} {path}"
            if any(marker in blob for marker in SUSPICIOUS_PROCESS_MARKERS) or any(marker in path for marker in TEMP_PATH_MARKERS) and "powershell" in blob:
                findings.append(
                    DetectionFinding(
                        rule_id="suspicious_process",
                        title="Suspicious process pattern",
                        severity="high",
                        confidence=0.66,
                        risk_score=70,
                        recommended_next_step="Inspect the process tree and parent, and confirm whether the activity is expected administration.",
                        evidence={"payload": payload},
                        event_ids=[str(event.get("id") or "")] if event.get("id") else [],
                        device_id=event.get("device_id"),
                    )
                )
        return findings

    def _unusual_outbound(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        conns = [e for e in events if e.get("category") == "network"]
        remotes = set()
        for event in conns:
            payload = event.get("payload") or event.get("payload_json") or {}
            remote = payload.get("remote_addr") or payload.get("raddr")
            if remote:
                remotes.add(str(remote))
                if self.threat_intel.match(str(remote)):
                    return [
                        DetectionFinding(
                            rule_id="threat_intel_match",
                            title="Network indicator matched threat intelligence",
                            severity="high",
                            confidence=0.6,
                            risk_score=75,
                            recommended_next_step="Review the connection and block the indicator if confirmed malicious.",
                            evidence={"indicator": remote},
                            device_id=event.get("device_id"),
                        )
                    ]
        if len(remotes) >= 40:
            return [
                DetectionFinding(
                    rule_id="unusual_outbound",
                    title="Unusual volume of outbound destinations",
                    severity="medium",
                    confidence=0.55,
                    risk_score=50,
                    recommended_next_step="Review outbound destinations against expected software on this device.",
                    evidence={"unique_remotes": len(remotes)},
                    event_ids=[str(e.get("id") or "") for e in conns if e.get("id")],
                    device_id=conns[0].get("device_id") if conns else None,
                )
            ]
        return []

    def _posture(self, events: list[dict[str, Any]]) -> list[DetectionFinding]:
        findings: list[DetectionFinding] = []
        for event in events:
            if event.get("category") != "agent_health":
                continue
            payload = event.get("payload") or event.get("payload_json") or {}
            if payload.get("running_as_admin") is False and payload.get("can_read_security_log") is False:
                findings.append(
                    DetectionFinding(
                        rule_id="limited_telemetry",
                        title="Agent cannot read Windows Security events",
                        severity="low",
                        confidence=0.9,
                        risk_score=25,
                        recommended_next_step="Run the agent with permission to read the Security event log, or accept reduced visibility.",
                        evidence={"payload": payload},
                        device_id=event.get("device_id"),
                        finding_type="vulnerability",
                    )
                )
        return findings

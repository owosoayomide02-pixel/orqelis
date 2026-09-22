from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AIAnalysis,
    AIUsage,
    Alert,
    Incident,
    IncidentEvent,
    SecurityEvent,
    Vulnerability,
    new_id,
)
from orqelis_ai.gateway import AIGateway
from orqelis_detection.engine import DetectionEngine

engine = DetectionEngine()
log = logging.getLogger("orqelis.ingest")


def event_to_dict(row: SecurityEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "organization_id": row.organization_id,
        "category": row.category,
        "event_type": row.event_type,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "payload": row.payload_json,
        "payload_json": row.payload_json,
    }


async def persist_events(
    db: AsyncSession,
    *,
    organization_id: str,
    device_id: str,
    items: list[dict[str, Any]],
) -> list[SecurityEvent]:
    rows: list[SecurityEvent] = []
    for item in items:
        occurred = item.get("occurred_at")
        if isinstance(occurred, str):
            try:
                occurred_at = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
            except ValueError:
                occurred_at = datetime.now(UTC)
        else:
            occurred_at = datetime.now(UTC)
        row = SecurityEvent(
            id=new_id(),
            organization_id=organization_id,
            device_id=device_id,
            category=str(item.get("category") or "agent_health"),
            event_type=str(item.get("event_type") or item.get("type") or "snapshot"),
            occurred_at=occurred_at,
            payload_json=item.get("payload") or item.get("payload_json") or {},
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def _open_alert(db: AsyncSession, organization_id: str, device_id: str, rule_id: str) -> Alert | None:
    return (
        await db.execute(
            select(Alert).where(
                Alert.organization_id == organization_id,
                Alert.device_id == device_id,
                Alert.rule_id == rule_id,
                Alert.status == "open",
            )
        )
    ).scalars().first()


async def _open_vuln(db: AsyncSession, organization_id: str, device_id: str, title: str) -> Vulnerability | None:
    return (
        await db.execute(
            select(Vulnerability).where(
                Vulnerability.organization_id == organization_id,
                Vulnerability.device_id == device_id,
                Vulnerability.title == title,
                Vulnerability.status == "open",
            )
        )
    ).scalars().first()


async def _open_incident(db: AsyncSession, organization_id: str, device_id: str, title: str) -> Incident | None:
    return (
        await db.execute(
            select(Incident).where(
                Incident.organization_id == organization_id,
                Incident.device_id == device_id,
                Incident.title == title,
                Incident.status.in_(("open", "investigating")),
            )
        )
    ).scalars().first()


async def apply_detections(
    db: AsyncSession,
    *,
    organization_id: str,
    device_id: str,
    events: list[SecurityEvent],
) -> dict[str, Any]:
    findings = engine.analyze([event_to_dict(row) for row in events])
    alerts: list[Alert] = []
    created_alerts: list[Alert] = []
    vulns: list[Vulnerability] = []
    now = datetime.now(UTC)
    for finding in findings:
        evidence = dict(finding.evidence or {})
        evidence["last_seen_at"] = now.isoformat()
        if finding.finding_type == "vulnerability":
            existing_vuln = await _open_vuln(db, organization_id, device_id, finding.title)
            if existing_vuln:
                existing_vuln.description = finding.recommended_next_step
                existing_vuln.severity = finding.severity
                existing_vuln.evidence_json = evidence
                vulns.append(existing_vuln)
                continue
            vuln = Vulnerability(
                id=new_id(),
                organization_id=organization_id,
                device_id=device_id,
                title=finding.title,
                description=finding.recommended_next_step,
                severity=finding.severity,
                source="posture",
                evidence_json=evidence,
            )
            db.add(vuln)
            vulns.append(vuln)
            continue
        existing = await _open_alert(db, organization_id, device_id, finding.rule_id)
        if existing:
            existing.title = finding.title
            existing.severity = finding.severity
            existing.confidence = finding.confidence
            existing.risk_score = finding.risk_score
            existing.evidence_json = evidence
            existing.recommended_next_step = finding.recommended_next_step
            alerts.append(existing)
            continue
        alert = Alert(
            id=new_id(),
            organization_id=organization_id,
            device_id=device_id,
            title=finding.title,
            severity=finding.severity,
            confidence=finding.confidence,
            risk_score=finding.risk_score,
            detection_source="rule",
            rule_id=finding.rule_id,
            evidence_json=evidence,
            recommended_next_step=finding.recommended_next_step,
        )
        db.add(alert)
        alerts.append(alert)
        created_alerts.append(alert)
    incidents_out = []
    for grouped in engine.correlate(findings):
        grouped_device = grouped.get("device_id") or device_id
        existing_incident = await _open_incident(db, organization_id, grouped_device, grouped["title"])
        if existing_incident:
            existing_incident.summary = grouped["summary"]
            existing_incident.severity = grouped["severity"]
            existing_incident.risk_score = grouped["risk_score"]
            existing_incident.updated_at = now
            incidents_out.append(existing_incident)
            continue
        incident = Incident(
            id=new_id(),
            organization_id=organization_id,
            device_id=grouped_device,
            title=grouped["title"],
            summary=grouped["summary"],
            severity=grouped["severity"],
            risk_score=grouped["risk_score"],
        )
        db.add(incident)
        await db.flush()
        for finding in grouped["findings"]:
            match = next((a for a in alerts if a.rule_id == finding.rule_id and a.title == finding.title), None)
            db.add(
                IncidentEvent(
                    id=new_id(),
                    incident_id=incident.id,
                    alert_id=match.id if match else None,
                    event_id=finding.event_ids[0] if finding.event_ids else None,
                )
            )
            if match:
                match.incident_id = incident.id
        incidents_out.append(incident)
    await db.flush()
    await auto_analyze_significant(db, organization_id, created_alerts)
    return {"alerts": alerts, "incidents": incidents_out, "vulnerabilities": vulns, "created_alerts": created_alerts}


async def store_analysis(
    db: AsyncSession,
    gateway: AIGateway,
    *,
    organization_id: str,
    role: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any],
) -> AIAnalysis:
    result = gateway.analyze(role=role, subject_type=subject_type, payload=payload)
    row = AIAnalysis(
        id=new_id(),
        organization_id=organization_id,
        role=role,
        subject_type=subject_type,
        subject_id=subject_id,
        provider=result.provider,
        model=result.model,
        input_redacted_json={"subject_type": subject_type, "subject_id": subject_id},
        output_json=result.output,
    )
    db.add(row)
    db.add(
        AIUsage(
            id=new_id(),
            organization_id=organization_id,
            provider=result.provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            estimated_cost_cents=result.estimated_cost_cents,
        )
    )
    await db.flush()
    return row


def _alert_payload(alert: Alert) -> dict[str, Any]:
    return {
        "title": alert.title,
        "severity": alert.severity,
        "risk_score": alert.risk_score,
        "evidence": alert.evidence_json,
        "recommended_next_step": alert.recommended_next_step,
    }


def _gateway() -> AIGateway:
    from app.config import settings

    return AIGateway(
        provider=settings.resolved_ai_provider,
        api_key=settings.resolved_ai_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
    )


async def auto_analyze_significant(
    db: AsyncSession,
    organization_id: str,
    alerts: list[Alert],
    *,
    limit: int = 2,
) -> int:
    """Sentinel-triage new high/critical alerts. Never remediates. Failures must not block ingest."""
    candidates = [row for row in alerts if (row.severity or "").lower() in {"high", "critical"}]
    candidates.sort(key=lambda row: row.risk_score or 0, reverse=True)
    gateway = _gateway()
    count = 0
    for alert in candidates[:limit]:
        existing = (
            await db.execute(
                select(AIAnalysis).where(
                    AIAnalysis.organization_id == organization_id,
                    AIAnalysis.subject_type == "alert",
                    AIAnalysis.subject_id == alert.id,
                    AIAnalysis.role == "sentinel",
                )
            )
        ).scalars().first()
        if existing:
            continue
        try:
            await store_analysis(
                db,
                gateway,
                organization_id=organization_id,
                role="sentinel",
                subject_type="alert",
                subject_id=alert.id,
                payload=_alert_payload(alert),
            )
            count += 1
        except Exception:
            log.exception("Auto Sentinel analysis failed for alert %s", alert.id)
    return count

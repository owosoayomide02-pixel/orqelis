from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership, require_rank
from app.emailer import send_email
from app.models import AIAnalysis, Alert, Device, Incident, Membership, Report, User, Vulnerability, new_id
from app.scoring import compute_score

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("")
async def list_reports(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(select(Report).where(Report.organization_id == membership.organization_id).order_by(Report.created_at.desc()))
    ).scalars().all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "body_markdown": row.body_markdown,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("")
async def generate_report(
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
) -> dict:
    org_id = membership.organization_id
    now = datetime.now(UTC)
    start = now - timedelta(days=7)
    device_rows = (await db.execute(select(Device).where(Device.organization_id == org_id))).scalars().all()
    alert_rows = (await db.execute(select(Alert).where(Alert.organization_id == org_id))).scalars().all()
    incident_rows = (await db.execute(select(Incident).where(Incident.organization_id == org_id))).scalars().all()
    vuln_rows = (await db.execute(select(Vulnerability).where(Vulnerability.organization_id == org_id))).scalars().all()
    score = compute_score(devices=list(device_rows), alerts=list(alert_rows), incidents=list(incident_rows), vulnerabilities=list(vuln_rows))
    open_high = [row for row in alert_rows if row.status == "open" and row.severity in {"high", "critical"}]
    analyses = (
        await db.execute(
            select(AIAnalysis)
            .where(AIAnalysis.organization_id == org_id, AIAnalysis.role == "sentinel")
            .order_by(AIAnalysis.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    score_line = "n/a (no enrolled devices)" if score["score"] is None else str(score["score"])
    alert_lines = "\n".join(f"- {row.severity}: {row.title}" for row in open_high[:8]) or "- None"
    ai_lines = "\n".join(
        f"- {row.subject_type} {row.subject_id}: {(row.output_json or {}).get('explanation', '')[:280]}"
        for row in analyses
    ) or "- No Sentinel analyses yet"
    body = (
        f"# Orqelis security report\n\n"
        f"Period: {start.date()} to {now.date()}\n\n"
        f"## Counts\n"
        f"- Devices: {len(device_rows)}\n"
        f"- Alerts: {len(alert_rows)}\n"
        f"- Incidents: {len(incident_rows)}\n"
        f"- Posture findings: {len(vuln_rows)}\n"
        f"- Security Score: {score_line}\n\n"
        f"## Open high and critical alerts\n{alert_lines}\n\n"
        f"## Sentinel analyses\n{ai_lines}\n\n"
        "This report is generated from tenant-isolated telemetry and detections. "
        "It is not a guarantee that every threat was identified. "
        "AI text explains findings; it does not perform remediation.\n"
    )
    row = Report(
        id=new_id(),
        organization_id=org_id,
        title=f"Weekly security report {now.date()}",
        body_markdown=body,
        period_start=start,
        period_end=now,
        created_by_user_id=membership.user_id,
    )
    db.add(row)
    user = await db.get(User, membership.user_id)
    if user:
        send_email(user.email, row.title, body)
    await db.commit()
    return {"id": row.id, "title": row.title, "body_markdown": row.body_markdown, "digest_emailed": True}

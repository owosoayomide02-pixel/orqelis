from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.database import get_db
from app.deps import get_membership, require_rank
from app.models import Incident, IncidentEvent, Membership

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


class StatusPayload(BaseModel):
    status: str


@router.get("")
async def list_incidents(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(
            select(Incident)
            .where(Incident.organization_id == membership.organization_id)
            .order_by(Incident.created_at.desc())
        )
    ).scalars().all()
    return [_out(row) for row in rows]


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    row = await db.get(Incident, incident_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    links = (await db.execute(select(IncidentEvent).where(IncidentEvent.incident_id == row.id))).scalars().all()
    data = _out(row)
    data["event_ids"] = [item.event_id for item in links if item.event_id]
    data["alert_ids"] = [item.alert_id for item in links if item.alert_id]
    return data


@router.post("/{incident_id}/status")
async def update_status(
    incident_id: str,
    payload: StatusPayload,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
) -> dict:
    allowed = {"open", "investigating", "contained", "resolved", "false_positive"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    row = await db.get(Incident, incident_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    row.status = payload.status
    await write_audit(
        db,
        action="incident.status",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="incident",
        resource_id=row.id,
        details={"status": payload.status},
    )
    await db.commit()
    return _out(row)


def _out(row: Incident) -> dict:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "title": row.title,
        "summary": row.summary,
        "severity": row.severity,
        "status": row.status,
        "risk_score": row.risk_score,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }

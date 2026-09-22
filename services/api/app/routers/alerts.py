from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership
from app.models import Alert, Membership

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    query = select(Alert).where(Alert.organization_id == membership.organization_id)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    rows = (await db.execute(query.order_by(Alert.created_at.desc()).limit(limit))).scalars().all()
    return [_out(row) for row in rows]


@router.get("/{alert_id}")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    row = await db.get(Alert, alert_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _out(row)


def _out(row: Alert) -> dict:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "title": row.title,
        "severity": row.severity,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "detection_source": row.detection_source,
        "rule_id": row.rule_id,
        "evidence": row.evidence_json,
        "recommended_next_step": row.recommended_next_step,
        "status": row.status,
        "incident_id": row.incident_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

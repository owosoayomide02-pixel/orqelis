from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership
from app.models import Membership, SecurityEvent

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("")
async def list_events(
    device_id: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    query = select(SecurityEvent).where(SecurityEvent.organization_id == membership.organization_id)
    if device_id:
        query = query.where(SecurityEvent.device_id == device_id)
    if category:
        query = query.where(SecurityEvent.category == category)
    rows = (await db.execute(query.order_by(SecurityEvent.occurred_at.desc()).limit(limit))).scalars().all()
    return [
        {
            "id": row.id,
            "device_id": row.device_id,
            "category": row.category,
            "event_type": row.event_type,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            "payload": row.payload_json,
        }
        for row in rows
    ]

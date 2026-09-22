from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership
from app.models import Membership, Vulnerability

router = APIRouter(prefix="/api/v1/vulnerabilities", tags=["vulnerabilities"])


@router.get("")
async def list_vulnerabilities(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(
            select(Vulnerability)
            .where(Vulnerability.organization_id == membership.organization_id)
            .order_by(Vulnerability.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "device_id": row.device_id,
            "title": row.title,
            "description": row.description,
            "severity": row.severity,
            "status": row.status,
            "source": row.source,
            "evidence": row.evidence_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

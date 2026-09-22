from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership, require_rank
from app.models import Membership, Policy

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


class PolicyUpdate(BaseModel):
    collect_process_metadata: bool | None = None
    collect_security_events: bool | None = None
    collect_network_metadata: bool | None = None
    heartbeat_seconds: int | None = None
    batch_max_events: int | None = None


@router.get("")
async def get_policy(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    row = (await db.execute(select(Policy).where(Policy.organization_id == membership.organization_id))).scalars().first()
    if row is None:
        return {}
    return _out(row)


@router.post("")
async def update_policy(
    payload: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict:
    row = (await db.execute(select(Policy).where(Policy.organization_id == membership.organization_id))).scalars().first()
    if row is None:
        from app.models import new_id

        row = Policy(id=new_id(), organization_id=membership.organization_id)
        db.add(row)
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(row, key, value)
    await db.commit()
    return _out(row)


def _out(row: Policy) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "collect_process_metadata": row.collect_process_metadata,
        "collect_security_events": row.collect_security_events,
        "collect_network_metadata": row.collect_network_metadata,
        "heartbeat_seconds": row.heartbeat_seconds,
        "batch_max_events": row.batch_max_events,
    }

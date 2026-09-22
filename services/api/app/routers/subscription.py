from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.deps import get_membership, require_rank
from app.models import Membership, Plan, Subscription
from app.payments import DevelopmentPaymentProvider

router = APIRouter(prefix="/api/v1/subscription", tags=["subscription"])


class ActivatePayload(BaseModel):
    plan_code: str


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(Plan).where(Plan.is_public.is_(True)))).scalars().all()
    return [_plan(row) for row in rows]


@router.get("")
async def get_subscription(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    row = (
        await db.execute(select(Subscription).where(Subscription.organization_id == membership.organization_id))
    ).scalar_one_or_none()
    plan = await db.get(Plan, row.plan_id) if row and row.plan_id else None
    return {
        "status": row.status if row else "none",
        "provider": row.provider if row else None,
        "plan": _plan(plan) if plan else None,
        "current_period_end": row.current_period_end.isoformat() if row and row.current_period_end else None,
    }


@router.post("/activate")
async def activate(
    payload: ActivatePayload,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("OWNER")),
) -> dict:
    if not settings.is_development:
        raise HTTPException(status_code=400, detail="Live payments are not configured. Contact sales for production billing.")
    plan = (await db.execute(select(Plan).where(Plan.code == payload.plan_code))).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.contact_sales:
        raise HTTPException(status_code=400, detail="Enterprise plans require contacting sales")
    row = (
        await db.execute(select(Subscription).where(Subscription.organization_id == membership.organization_id))
    ).scalar_one_or_none()
    if row is None:
        from app.models import new_id

        row = Subscription(id=new_id(), organization_id=membership.organization_id)
        db.add(row)
    row.plan_id = plan.id
    row.status = "active"
    row.provider = DevelopmentPaymentProvider().name
    row.current_period_end = datetime.now(UTC) + timedelta(days=30)
    await write_audit(
        db,
        action="subscription.activate",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="subscription",
        resource_id=row.id,
        details={"plan": plan.code, "provider": "development"},
    )
    await db.commit()
    return {"status": row.status, "plan": _plan(plan), "provider": "development"}


def _plan(row: Plan) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "monthly_price_cents": row.monthly_price_cents,
        "currency": row.currency,
        "contact_sales": row.contact_sales,
        "features": row.features_json,
    }

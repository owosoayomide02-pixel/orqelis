"""Plan-tier limits for web assets and Hunter scans, enforced server-side."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Plan, ScanJob, Subscription, WebAsset

SCAN_WINDOW = timedelta(days=30)

# None means unlimited. Orgs without an active subscription fall back to the free allowance in settings.
PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "solo": {"web_assets": 3, "scans_monthly": 10},
    "starter": {"web_assets": 5, "scans_monthly": 25},
    "pro": {"web_assets": 15, "scans_monthly": 100},
    "agency": {"web_assets": 25, "scans_monthly": None},
    "enterprise": {"web_assets": None, "scans_monthly": None},
    # Retired catalog codes: kept so existing subscriptions on them are not silently downgraded to free.
    "personal": {"web_assets": 3, "scans_monthly": 30},
    "business_core": {"web_assets": 25, "scans_monthly": 500},
}

ACTIVE_STATUSES = {"active", "trialing", "trial"}


async def org_limits(db: AsyncSession, organization_id: str) -> dict[str, Any]:
    sub = (
        await db.execute(select(Subscription).where(Subscription.organization_id == organization_id))
    ).scalar_one_or_none()
    plan = await db.get(Plan, sub.plan_id) if sub and sub.plan_id and sub.status in ACTIVE_STATUSES else None
    if plan is not None and plan.code in PLAN_LIMITS:
        limits = PLAN_LIMITS[plan.code]
        return {"plan_code": plan.code, "plan_name": plan.name, **limits}
    return {
        "plan_code": "free",
        "plan_name": "No active plan",
        "web_assets": settings.web_asset_quota_free,
        "scans_monthly": settings.scan_quota_per_org_monthly,
    }


async def web_asset_count(db: AsyncSession, organization_id: str) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(WebAsset)
                .where(WebAsset.organization_id == organization_id, WebAsset.archived.is_(False))
            )
        ).scalar_one()
        or 0
    )


async def monthly_scan_count(db: AsyncSession, organization_id: str) -> int:
    since = datetime.now(UTC) - SCAN_WINDOW
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(ScanJob)
                .where(ScanJob.organization_id == organization_id, ScanJob.created_at >= since)
            )
        ).scalar_one()
        or 0
    )


async def usage(db: AsyncSession, organization_id: str) -> dict[str, Any]:
    limits = await org_limits(db, organization_id)
    return {
        "plan_code": limits["plan_code"],
        "plan_name": limits["plan_name"],
        "scan_window_days": SCAN_WINDOW.days,
        "web_assets": {"used": await web_asset_count(db, organization_id), "limit": limits["web_assets"]},
        "scans": {"used": await monthly_scan_count(db, organization_id), "limit": limits["scans_monthly"]},
    }

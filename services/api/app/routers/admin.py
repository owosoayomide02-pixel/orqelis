from datetime import UTC, datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.deps import ADMIN_COOKIE_NAME, get_internal_user
from app.models import (
    AIUsage,
    AgentVersion,
    Alert,
    AuditLog,
    Device,
    Incident,
    InternalSession,
    InternalUser,
    Membership,
    Organization,
    Plan,
    Subscription,
    SystemIncident,
    User,
    Vulnerability,
    WebAsset,
    new_id,
)
from orqelis_security.passwords import verify_password
from orqelis_security.rate_limit import RateLimiter
from orqelis_security.tokens import hash_secret, new_secret

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
limiter = RateLimiter(settings.auth_rate_limit_per_minute)


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def _money(cents: int, currency: str = "USD") -> dict:
    return {
        "cents": cents,
        "currency": currency,
        "formatted": f"${cents / 100:,.2f}" if currency.upper() == "USD" else f"{cents / 100:,.2f} {currency}",
    }


@router.post("/login")
async def login(payload: AdminLogin, request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    ip = request.client.host if request.client else ""
    if not limiter.allow(f"admin:{ip}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    user = (await db.execute(select(InternalUser).where(InternalUser.email == payload.email.lower()))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    raw = new_secret()
    db.add(
        InternalSession(
            id=new_id(),
            internal_user_id=user.id,
            token_hash=hash_secret(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
        )
    )
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        raw,
        httponly=True,
        samesite="lax",
        secure=settings.resolved_cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    await write_audit(db, action="admin.login", actor_type="internal", actor_id=user.id, ip_address=ip)
    await db.commit()
    return {"id": user.id, "email": user.email, "role": user.role, "display_name": user.display_name}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: InternalUser = Depends(get_internal_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name or "Founder",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db), user: InternalUser = Depends(get_internal_user)) -> dict:
    orgs = (await db.execute(select(func.count()).select_from(Organization))).scalar() or 0
    users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    devices = (await db.execute(select(func.count()).select_from(Device))).scalar() or 0
    alerts = (await db.execute(select(func.count()).select_from(Alert))).scalar() or 0
    open_alerts = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))
    ).scalar() or 0
    incidents = (await db.execute(select(func.count()).select_from(Incident))).scalar() or 0
    open_incidents = (
        await db.execute(select(func.count()).select_from(Incident).where(Incident.status == "open"))
    ).scalar() or 0
    vulnerabilities = (await db.execute(select(func.count()).select_from(Vulnerability))).scalar() or 0
    web_assets = (await db.execute(select(func.count()).select_from(WebAsset))).scalar() or 0
    active_subs = (
        await db.execute(select(func.count()).select_from(Subscription).where(Subscription.status == "active"))
    ).scalar() or 0
    trial_subs = (
        await db.execute(select(func.count()).select_from(Subscription).where(Subscription.status.in_(["trialing", "trial"])))
    ).scalar() or 0
    none_subs = (
        await db.execute(select(func.count()).select_from(Subscription).where(Subscription.status.in_(["none", "canceled", "cancelled"])))
    ).scalar() or 0

    plans = (await db.execute(select(Plan).order_by(Plan.monthly_price_cents.desc()))).scalars().all()
    plan_by_id = {row.id: row for row in plans}

    subs = (await db.execute(select(Subscription).order_by(Subscription.updated_at.desc()))).scalars().all()
    org_rows = (await db.execute(select(Organization).order_by(Organization.created_at.desc()))).scalars().all()
    org_by_id = {row.id: row for row in org_rows}

    member_counts = {
        org_id: count
        for org_id, count in (
            await db.execute(select(Membership.organization_id, func.count()).group_by(Membership.organization_id))
        ).all()
    }
    device_counts = {
        org_id: count
        for org_id, count in (await db.execute(select(Device.organization_id, func.count()).group_by(Device.organization_id))).all()
    }

    mrr_cents = 0
    arr_cents = 0
    plan_breakdown: dict[str, dict] = {}
    subscription_rows: list[dict] = []
    for sub in subs:
        plan = plan_by_id.get(sub.plan_id) if sub.plan_id else None
        price = plan.monthly_price_cents if plan else 0
        currency = plan.currency if plan else "USD"
        org = org_by_id.get(sub.organization_id)
        if sub.status == "active" and price > 0:
            mrr_cents += price
            key = plan.code if plan else "unknown"
            bucket = plan_breakdown.setdefault(
                key,
                {
                    "plan_code": key,
                    "plan_name": plan.name if plan else "Unknown",
                    "subscribers": 0,
                    "mrr_cents": 0,
                    "monthly_price_cents": price,
                    "currency": currency,
                },
            )
            bucket["subscribers"] += 1
            bucket["mrr_cents"] += price
        subscription_rows.append(
            {
                "id": sub.id,
                "organization_id": sub.organization_id,
                "organization_name": org.name if org else "Unknown org",
                "organization_slug": org.slug if org else "",
                "status": sub.status,
                "provider": sub.provider,
                "plan_code": plan.code if plan else None,
                "plan_name": plan.name if plan else None,
                "monthly_price_cents": price,
                "currency": currency,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
            }
        )
    arr_cents = mrr_cents * 12

    # Ledger-style transactions from subscription activations + priced active subs as recurring charges
    billing_audits = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.action.in_(["subscription.activate", "subscription.cancel", "subscription.update"]))
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    transactions: list[dict] = []
    recognized_revenue_cents = 0
    for row in billing_audits:
        details = row.details_json or {}
        plan_code = details.get("plan") or details.get("plan_code") or ""
        plan = next((p for p in plans if p.code == plan_code), None)
        amount = plan.monthly_price_cents if plan and row.action == "subscription.activate" else 0
        if amount:
            recognized_revenue_cents += amount
        org = org_by_id.get(row.organization_id) if row.organization_id else None
        transactions.append(
            {
                "id": row.id,
                "type": row.action,
                "status": "posted",
                "organization_name": org.name if org else details.get("organization_name") or "—",
                "plan_code": plan_code or None,
                "plan_name": plan.name if plan else None,
                "provider": details.get("provider") or "development",
                "amount_cents": amount,
                "currency": plan.currency if plan else "USD",
                "amount": _money(amount, plan.currency if plan else "USD"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "actor_type": row.actor_type,
            }
        )

    # If no audit ledger yet, synthesize recurring charge rows from active paid subscriptions
    if not transactions:
        for row in subscription_rows:
            if row["status"] == "active" and (row["monthly_price_cents"] or 0) > 0:
                transactions.append(
                    {
                        "id": f"synth-{row['id']}",
                        "type": "subscription.recurring",
                        "status": "projected",
                        "organization_name": row["organization_name"],
                        "plan_code": row["plan_code"],
                        "plan_name": row["plan_name"],
                        "provider": row["provider"],
                        "amount_cents": row["monthly_price_cents"],
                        "currency": row["currency"],
                        "amount": _money(row["monthly_price_cents"], row["currency"]),
                        "created_at": row["updated_at"] or row["created_at"],
                        "actor_type": "system",
                    }
                )

    ai_rows = (await db.execute(select(AIUsage))).scalars().all()
    ai_cost_cents = sum(row.estimated_cost_cents for row in ai_rows)
    versions = (await db.execute(select(AgentVersion))).scalars().all()
    system_incidents = (
        await db.execute(select(SystemIncident).order_by(SystemIncident.created_at.desc()).limit(20))
    ).scalars().all()

    recent_users = (
        await db.execute(select(User).order_by(User.created_at.desc()).limit(12))
    ).scalars().all()

    organizations_detail = []
    for org in org_rows[:40]:
        sub = next((s for s in subscription_rows if s["organization_id"] == org.id), None)
        organizations_detail.append(
            {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "members": member_counts.get(org.id, 0),
                "devices": device_counts.get(org.id, 0),
                "subscription_status": sub["status"] if sub else "none",
                "plan_name": sub["plan_name"] if sub else None,
                "mrr_cents": sub["monthly_price_cents"] if sub and sub["status"] == "active" else 0,
                "created_at": org.created_at.isoformat() if org.created_at else None,
            }
        )

    provider_counts = Counter(row["provider"] for row in subscription_rows)
    gross_margin_cents = mrr_cents - ai_cost_cents

    return {
        "viewer": {
            "id": user.id,
            "role": user.role,
            "email": user.email,
            "display_name": user.display_name or "Founder",
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "organizations": orgs,
        "users": users,
        "devices": devices,
        "alerts_processed": alerts,
        "open_alerts": open_alerts,
        "incidents": incidents,
        "open_incidents": open_incidents,
        "vulnerabilities": vulnerabilities,
        "web_assets": web_assets,
        "active_subscriptions": active_subs,
        "trial_subscriptions": trial_subs,
        "inactive_subscriptions": none_subs,
        "environment": settings.environment,
        "api_ok": True,
        "billing_live": False,
        "revenue": {
            "mrr_cents": mrr_cents,
            "arr_cents": arr_cents,
            "recognized_revenue_cents": recognized_revenue_cents or mrr_cents,
            "ai_cost_cents": ai_cost_cents,
            "gross_margin_cents": gross_margin_cents,
            "currency": "USD",
            "mrr": _money(mrr_cents),
            "arr": _money(arr_cents),
            "recognized_revenue": _money(recognized_revenue_cents or mrr_cents),
            "ai_cost": _money(ai_cost_cents),
            "gross_margin": _money(gross_margin_cents),
            "paying_customers": sum(1 for row in subscription_rows if row["status"] == "active" and (row["monthly_price_cents"] or 0) > 0),
            "arpu_cents": int(mrr_cents / active_subs) if active_subs else 0,
            "arpu": _money(int(mrr_cents / active_subs) if active_subs else 0),
            "note": "MRR is calculated from active subscriptions × plan monthly_price_cents. Live Stripe/Paystack charging is not enabled in v0.1.0.",
        },
        "plan_breakdown": sorted(plan_breakdown.values(), key=lambda item: item["mrr_cents"], reverse=True),
        "plans": [
            {
                "code": plan.code,
                "name": plan.name,
                "monthly_price_cents": plan.monthly_price_cents,
                "currency": plan.currency,
                "contact_sales": plan.contact_sales,
                "price": _money(plan.monthly_price_cents, plan.currency),
            }
            for plan in plans
        ],
        "subscriptions": subscription_rows[:50],
        "transactions": transactions[:50],
        "transaction_summary": {
            "count": len(transactions),
            "posted_volume_cents": sum(t["amount_cents"] for t in transactions if t.get("status") in {"posted", "projected"}),
            "posted_volume": _money(sum(t["amount_cents"] for t in transactions if t.get("status") in {"posted", "projected"})),
            "providers": dict(provider_counts),
        },
        "organizations_detail": organizations_detail,
        "recent_users": [
            {
                "id": row.id,
                "email": row.email,
                "display_name": row.display_name or row.email.split("@")[0],
                "email_verified": bool(row.email_verified_at),
                "mfa_enabled": row.mfa_enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in recent_users
        ],
        "agent_versions": [
            {"platform": row.platform, "version": row.version, "notes": row.notes} for row in versions
        ],
        "system_incidents": [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "severity": row.severity,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in system_incidents
        ],
        "ai": {
            "requests": len(ai_rows),
            "prompt_tokens": sum(row.prompt_tokens for row in ai_rows),
            "completion_tokens": sum(row.completion_tokens for row in ai_rows),
            "estimated_cost_cents": ai_cost_cents,
            "estimated_cost": _money(ai_cost_cents),
        },
        "note": "Founder console shows platform aggregates, billing math, and org metadata — not raw customer endpoint telemetry.",
    }


@router.get("/audit")
async def platform_audit(db: AsyncSession = Depends(get_db), user: InternalUser = Depends(get_internal_user)) -> list[dict]:
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))).scalars().all()
    return [
        {
            "id": row.id,
            "action": row.action,
            "actor_type": row.actor_type,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "organization_id": row.organization_id,
            "details": row.details_json or {},
            "ip_address": row.ip_address,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/system-incidents")
async def system_incidents(db: AsyncSession = Depends(get_db), _: InternalUser = Depends(get_internal_user)) -> list[dict]:
    rows = (await db.execute(select(SystemIncident).order_by(SystemIncident.created_at.desc()))).scalars().all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "severity": row.severity,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

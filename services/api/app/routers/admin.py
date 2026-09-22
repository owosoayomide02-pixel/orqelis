from datetime import UTC, datetime, timedelta

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
    InternalSession,
    InternalUser,
    Organization,
    Subscription,
    SystemIncident,
    User,
    new_id,
)
from orqelis_security.passwords import hash_password, verify_password
from orqelis_security.rate_limit import RateLimiter
from orqelis_security.tokens import hash_secret, new_secret

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
limiter = RateLimiter(settings.auth_rate_limit_per_minute)


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


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
    return {"id": user.id, "email": user.email, "role": user.role, "display_name": user.display_name}


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db), user: InternalUser = Depends(get_internal_user)) -> dict:
    orgs = (await db.execute(select(func.count()).select_from(Organization))).scalar() or 0
    users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    devices = (await db.execute(select(func.count()).select_from(Device))).scalar() or 0
    alerts = (await db.execute(select(func.count()).select_from(Alert))).scalar() or 0
    active_subs = (
        await db.execute(select(func.count()).select_from(Subscription).where(Subscription.status == "active"))
    ).scalar() or 0
    ai_rows = (await db.execute(select(AIUsage))).scalars().all()
    versions = (await db.execute(select(AgentVersion))).scalars().all()
    incidents = (await db.execute(select(SystemIncident).order_by(SystemIncident.created_at.desc()).limit(20))).scalars().all()
    return {
        "viewer": {"id": user.id, "role": user.role, "email": user.email},
        "organizations": orgs,
        "users": users,
        "devices": devices,
        "alerts_processed": alerts,
        "active_subscriptions": active_subs,
        "environment": settings.environment,
        "api_ok": True,
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
            for row in incidents
        ],
        "ai": {
            "requests": len(ai_rows),
            "prompt_tokens": sum(row.prompt_tokens for row in ai_rows),
            "completion_tokens": sum(row.completion_tokens for row in ai_rows),
            "estimated_cost_cents": sum(row.estimated_cost_cents for row in ai_rows),
        },
        "note": "This console does not expose customer telemetry by default.",
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

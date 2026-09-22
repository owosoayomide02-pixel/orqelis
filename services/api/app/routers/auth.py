from __future__ import annotations

from datetime import UTC, datetime, timedelta
from re import sub
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.deps import COOKIE_NAME, get_current_user, get_session_user
from app.emailer import send_email
from app.mfa import decrypt_secret, encrypt_secret, new_totp_secret, otpauth_url, verify_totp
from app.models import (
    EmailToken,
    LoginAttempt,
    Membership,
    Organization,
    Policy,
    Subscription,
    User,
    UserSession,
    new_id,
)
from orqelis_security.passwords import hash_password, verify_password
from orqelis_security.rate_limit import RateLimiter
from orqelis_security.tokens import hash_secret, new_secret

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
auth_limiter = RateLimiter(settings.auth_rate_limit_per_minute)

def _cookie_opts() -> dict[str, Any]:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.resolved_cookie_secure,
        "max_age": settings.jwt_expire_minutes * 60,
        "path": "/",
    }


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)
    organization_name: str = Field(default="", max_length=160)
    accept_terms: bool
    acknowledge_privacy: bool
    marketing_opt_in: bool = False


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    totp: str = Field(default="", max_length=12)


class MfaCodePayload(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class MfaDisablePayload(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=12)


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyPayload(BaseModel):
    token: str


def _slug(name: str) -> str:
    base = sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "org"
    return f"{base}-{new_id()[:8]}"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


async def _create_session(db: AsyncSession, user: User, request: Request, response: Response) -> str:
    raw = new_secret()
    session = UserSession(
        id=new_id(),
        user_id=user.id,
        token_hash=hash_secret(raw),
        user_agent=request.headers.get("user-agent", "")[:400],
        ip_address=_client_ip(request),
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
    )
    db.add(session)
    response.set_cookie(COOKIE_NAME, raw, **_cookie_opts())
    return raw


async def _issue_email_token(db: AsyncSession, user: User, purpose: str, minutes: int = 60 * 24) -> str:
    raw = new_secret(24)
    db.add(
        EmailToken(
            id=new_id(),
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_secret(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=minutes),
        )
    )
    return raw


def _log_email_links() -> bool:
    return settings.is_development and (settings.email_backend or "log").lower() == "log"


def _user_out(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "email_verified": user.email_verified_at is not None,
        "mfa_enabled": user.mfa_enabled,
        "marketing_opt_in": user.marketing_opt_in,
        "dev_email_links": _log_email_links() and user.email_verified_at is None,
    }


@router.post("/register")
async def register(payload: RegisterPayload, request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> Any:
    if not auth_limiter.allow(f"register:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    if not payload.accept_terms or not payload.acknowledge_privacy:
        raise HTTPException(status_code=400, detail="Terms of Service and Privacy Policy must be accepted")
    email = payload.email.lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        id=new_id(),
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or email.split("@")[0],
        accepted_terms_at=datetime.now(UTC),
        accepted_privacy_at=datetime.now(UTC),
        marketing_opt_in=payload.marketing_opt_in,
    )
    org = Organization(
        id=new_id(),
        name=payload.organization_name or f"{user.display_name}'s organization",
        slug=_slug(payload.organization_name or user.display_name),
    )
    db.add(user)
    db.add(org)
    await db.flush()
    db.add(Membership(id=new_id(), user_id=user.id, organization_id=org.id, role="OWNER"))
    db.add(Policy(id=new_id(), organization_id=org.id, name="Default endpoint policy"))
    db.add(Subscription(id=new_id(), organization_id=org.id, status="none", provider="development"))
    token = await _issue_email_token(db, user, "verify")
    await _create_session(db, user, request, response)
    await write_audit(
        db,
        action="auth.register",
        actor_type="user",
        actor_id=user.id,
        organization_id=org.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
    )
    await db.commit()
    verify_url = f"{settings.app_base_url}/verify-email?token={token}"
    send_email(
        user.email,
        "Verify your Orqelis email",
        f"Welcome to Orqelis.\n\nVerify your email:\n{verify_url}\n\nIf you did not create this account, ignore this message.",
    )
    payload_out = {**_user_out(user), "organization_id": org.id, "role": "OWNER"}
    if _log_email_links():
        payload_out["verification_url"] = verify_url
        payload_out["verification_notice"] = "SMTP is unset. Use this link or the copy printed in the API log."
    return payload_out


@router.post("/login")
async def login(payload: LoginPayload, request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> Any:
    ip = _client_ip(request)
    if not auth_limiter.allow(f"login:{ip}:{payload.email.lower()}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    email = payload.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    db.add(LoginAttempt(id=new_id(), email=email, ip_address=ip, success=False))
    if user is None:
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = datetime.now(UTC)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Account temporarily locked")
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= 8:
            user.locked_until = now + timedelta(minutes=15)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.mfa_enabled:
        secret = decrypt_secret(user.mfa_secret_encrypted or "")
        if not payload.totp:
            await db.commit()
            return {"mfa_required": True, "email": user.email}
        if not verify_totp(secret, payload.totp):
            user.failed_login_count += 1
            await db.commit()
            raise HTTPException(status_code=401, detail="Invalid authenticator code")
    user.failed_login_count = 0
    user.locked_until = None
    await _create_session(db, user, request, response)
    await write_audit(db, action="auth.login", actor_type="user", actor_id=user.id, ip_address=ip)
    await db.commit()
    membership = (await db.execute(select(Membership).where(Membership.user_id == user.id))).scalars().first()
    return {
        **_user_out(user),
        "mfa_required": False,
        "organization_id": membership.organization_id if membership else None,
        "role": membership.role if membership else None,
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    pair: tuple[User, UserSession] = Depends(get_session_user),
) -> dict:
    user, session = pair
    session.revoked_at = datetime.now(UTC)
    response.delete_cookie(COOKIE_NAME, path="/")
    await write_audit(db, action="auth.logout", actor_type="user", actor_id=user.id, ip_address=_client_ip(request))
    await db.commit()
    return {"ok": True}


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> Any:
    memberships = (
        await db.execute(select(Membership).where(Membership.user_id == user.id))
    ).scalars().all()
    orgs = []
    for item in memberships:
        org = await db.get(Organization, item.organization_id)
        orgs.append(
            {
                "id": item.organization_id,
                "name": org.name if org else "",
                "role": item.role,
            }
        )
    return {**_user_out(user), "organizations": orgs}


@router.post("/mfa/setup")
async def mfa_setup(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Authenticator is already enabled")
    secret = new_totp_secret()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    await db.commit()
    return {"secret": secret, "otpauth_url": otpauth_url(user.email, secret)}


@router.post("/mfa/enable")
async def mfa_enable(
    payload: MfaCodePayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    secret = decrypt_secret(user.mfa_secret_encrypted or "")
    if not secret or not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    user.mfa_enabled = True
    await write_audit(db, action="auth.mfa.enable", actor_type="user", actor_id=user.id)
    await db.commit()
    return {"ok": True, "mfa_enabled": True}


@router.post("/mfa/disable")
async def mfa_disable(
    payload: MfaDisablePayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    secret = decrypt_secret(user.mfa_secret_encrypted or "")
    if user.mfa_enabled and not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    await write_audit(db, action="auth.mfa.disable", actor_type="user", actor_id=user.id)
    await db.commit()
    return {"ok": True, "mfa_enabled": False}


@router.post("/verification-link")
async def verification_link(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if not _log_email_links():
        raise HTTPException(status_code=404, detail="Verification links are emailed when SMTP is configured")
    if user.email_verified_at is not None:
        return {"ok": True, "email_verified": True, "verification_url": None}
    token = await _issue_email_token(db, user, "verify")
    await db.commit()
    verify_url = f"{settings.app_base_url}/verify-email?token={token}"
    send_email(
        user.email,
        "Verify your Orqelis email",
        f"Verify your email:\n{verify_url}\n",
    )
    return {
        "ok": True,
        "email_verified": False,
        "verification_url": verify_url,
        "notice": "SMTP is unset. This development link is also printed in the API log.",
    }


@router.post("/verify-email")
async def verify_email(payload: VerifyPayload, db: AsyncSession = Depends(get_db)) -> dict:
    row = (
        await db.execute(select(EmailToken).where(EmailToken.token_hash == hash_secret(payload.token), EmailToken.purpose == "verify"))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid token")
    expires = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Token expired")
    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.email_verified_at = datetime.now(UTC)
    row.used_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}


@router.post("/password-reset/request")
async def password_reset_request(payload: ResetRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    if not auth_limiter.allow(f"reset:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    user = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    reset_url = None
    if user:
        token = await _issue_email_token(db, user, "reset", minutes=60)
        await db.commit()
        reset_url = f"{settings.app_base_url}/reset-password?token={token}"
        send_email(user.email, "Reset your Orqelis password", f"Reset your password:\n{reset_url}\n")
    else:
        await db.commit()
    out: dict[str, Any] = {"ok": True}
    if _log_email_links() and reset_url:
        out["reset_url"] = reset_url
        out["notice"] = "SMTP is unset. Development reset link is included and printed in the API log."
    return out


@router.post("/password-reset/confirm")
async def password_reset_confirm(payload: ResetConfirm, db: AsyncSession = Depends(get_db)) -> dict:
    row = (
        await db.execute(select(EmailToken).where(EmailToken.token_hash == hash_secret(payload.token), EmailToken.purpose == "reset"))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid token")
    expires = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Token expired")
    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.password_hash = hash_password(payload.password)
    user.failed_login_count = 0
    user.locked_until = None
    row.used_at = datetime.now(UTC)
    sessions = (await db.execute(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)))).scalars().all()
    now = datetime.now(UTC)
    for session in sessions:
        session.revoked_at = now
    await db.commit()
    return {"ok": True}


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    rows = (
        await db.execute(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at.desc()))
    ).scalars().all()
    return [
        {
            "id": row.id,
            "user_agent": row.user_agent,
            "ip_address": row.ip_address,
            "created_at": row.created_at.isoformat(),
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "revoked": row.revoked_at is not None,
        }
        for row in rows
    ]


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = await db.get(UserSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    row.revoked_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models import Device, InternalSession, InternalUser, Membership, Organization, User, UserSession
from orqelis_security.tokens import hash_secret
from orqelis_shared.constants import CUSTOMER_ROLE_RANK

COOKIE_NAME = "orqelis_session"
ADMIN_COOKIE_NAME = "orqelis_admin"
DEVICE_HEADER = "X-Orqelis-Device-Token"
BEARER_PREFIX = "Bearer "


def issue_access_token(*, user_id: str, session_id: str, minutes: int | None = None) -> str:
    exp_minutes = minutes if minutes is not None else min(60, settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "typ": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=exp_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def issue_refresh_token(*, user_id: str, session_id: str) -> str:
    payload = {
        "sub": user_id,
        "sid": session_id,
        "typ": "refresh",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, *, expect_typ: str) -> dict[str, Any]:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if data.get("typ") != expect_typ:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return data


async def _user_from_session(db: AsyncSession, session: UserSession) -> User:
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")
    user = session.user if hasattr(session, "user") and session.user is not None else await db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_session_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, UserSession]:
    # Prefer cookie (web); fall back to Bearer access JWT (desktop)
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("Authorization") or ""
    if not token and auth.startswith(BEARER_PREFIX):
        claims = decode_token(auth[len(BEARER_PREFIX) :].strip(), expect_typ="access")
        session = (
            await db.execute(
                select(UserSession)
                .options(selectinload(UserSession.user))
                .where(UserSession.id == claims.get("sid"), UserSession.revoked_at.is_(None))
            )
        ).scalar_one_or_none()
        if session is None or session.user_id != claims.get("sub"):
            raise HTTPException(status_code=401, detail="Not authenticated")
        user = await _user_from_session(db, session)
        return user, session

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = (
        await db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.token_hash == hash_secret(token), UserSession.revoked_at.is_(None))
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await _user_from_session(db, session)
    return user, session


async def get_current_user(pair: tuple[User, UserSession] = Depends(get_session_user)) -> User:
    return pair[0]


async def get_membership(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Membership:
    org_id = request.headers.get("X-Organization-Id")
    query = select(Membership).options(selectinload(Membership.organization)).where(Membership.user_id == user.id)
    if org_id:
        query = query.where(Membership.organization_id == org_id)
    membership = (await db.execute(query.order_by(Membership.created_at.asc()))).scalars().first()
    if membership is None:
        raise HTTPException(status_code=403, detail="No organization membership")
    return membership


def require_role(*roles: str):
    async def _inner(membership: Membership = Depends(get_membership)) -> Membership:
        if membership.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return membership

    return _inner


def require_rank(minimum: str):
    needed = CUSTOMER_ROLE_RANK[minimum]

    async def _inner(membership: Membership = Depends(get_membership)) -> Membership:
        if CUSTOMER_ROLE_RANK.get(membership.role, 0) < needed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return membership

    return _inner


async def get_current_device(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Device:
    token = request.headers.get(DEVICE_HEADER)
    if not token:
        raise HTTPException(status_code=401, detail="Device token required")
    device = (
        await db.execute(select(Device).where(Device.token_hash == hash_secret(token), Device.revoked_at.is_(None)))
    ).scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid device token")
    return device


async def get_internal_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> InternalUser:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    auth = request.headers.get("Authorization") or ""
    if not token and auth.startswith(BEARER_PREFIX):
        # Supabase founder JWT: validated via service role when configured
        bearer = auth[len(BEARER_PREFIX) :].strip()
        user = await _internal_from_supabase(db, bearer)
        if user is not None:
            return user
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = (
        await db.execute(
            select(InternalSession).where(
                InternalSession.token_hash == hash_secret(token),
                InternalSession.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.get(InternalUser, session.internal_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def _internal_from_supabase(db: AsyncSession, bearer: str) -> InternalUser | None:
    """Accept Supabase access tokens for founder dashboard when SUPABASE_URL is set."""
    url = (settings.supabase_url or settings.next_public_supabase_url or "").rstrip("/")
    key = settings.supabase_service_role_key or settings.supabase_anon_key or settings.next_public_supabase_anon_key
    if not url or not key:
        return None
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{url}/auth/v1/user",
                headers={"Authorization": f"Bearer {bearer}", "apikey": key},
            )
            if resp.status_code >= 400:
                return None
            data = resp.json()
        email = (data.get("email") or "").lower()
        if not email:
            return None
        return (
            await db.execute(select(InternalUser).where(InternalUser.email == email))
        ).scalar_one_or_none()
    except Exception:
        return None


def org_filter(model, organization: Organization):
    return model.organization_id == organization.id

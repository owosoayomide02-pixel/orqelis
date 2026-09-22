from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Device, InternalSession, InternalUser, Membership, Organization, User, UserSession
from orqelis_security.tokens import hash_secret
from orqelis_shared.constants import CUSTOMER_ROLE_RANK

COOKIE_NAME = "orqelis_session"
ADMIN_COOKIE_NAME = "orqelis_admin"
DEVICE_HEADER = "X-Orqelis-Device-Token"


async def get_session_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, UserSession]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = (
        await db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.token_hash == hash_secret(token), UserSession.revoked_at.is_(None))
        )
    ).scalar_one_or_none()
    if session is None or session.expires_at.tzinfo is None:
        # compare in Python after load if needed
        pass
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from datetime import UTC, datetime

    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")
    return session.user, session


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
    from datetime import UTC, datetime

    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.get(InternalUser, session.internal_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def org_filter(model, organization: Organization):
    return model.organization_id == organization.id

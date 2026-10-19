from __future__ import annotations

import logging

import httpx
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import WaitlistEntry, utcnow

log = logging.getLogger("orqelis.waitlist")
router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])
RESEND_API_URL = "https://api.resend.com"


class WaitlistPayload(BaseModel):
    email: str = Field(max_length=254)
    website: str = Field(default="", max_length=256)


class ResendAPIError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Resend API returned {status_code}")


async def _resend_request(
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    allowed_statuses: tuple[int, ...] = (),
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.request(
            method,
            f"{RESEND_API_URL}{path}",
            headers={"Authorization": f"Bearer {settings.resend_api_key}", "Content-Type": "application/json"},
            json=body,
        )
    if not response.is_success and response.status_code not in allowed_statuses:
        raise ResendAPIError(response.status_code)
    return response


async def _send_waitlist_notification(email: str) -> None:
    recipient = settings.resend_waitlist_notification_email.strip() or settings.founder_email.strip()
    if not settings.resend_api_key.strip() or not settings.resend_from_email.strip() or not recipient:
        raise RuntimeError("Resend notification settings are incomplete")
    await _resend_request(
        "/emails",
        method="POST",
        body={
            "from": settings.resend_from_email,
            "to": [recipient],
            "subject": "New Orqelis waitlist signup",
            "text": f"A new email address joined the Orqelis waitlist:\n\n{email}",
        },
    )


async def _sync_resend_contact(email: str) -> None:
    if not settings.resend_api_key.strip():
        raise RuntimeError("Resend contact sync settings are incomplete")

    await _resend_request(
        "/contacts",
        method="POST",
        body={"email": email, "unsubscribed": False},
        allowed_statuses=(409,),
    )


async def _get_entry(db: AsyncSession, email: str) -> WaitlistEntry | None:
    return (
        await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    ).scalar_one_or_none()


def _log_provider_failure(operation: str, exc: Exception) -> None:
    if isinstance(exc, ResendAPIError):
        log.warning("Waitlist %s failed with Resend status %d", operation, exc.status_code)
    else:
        log.warning("Waitlist %s failed (%s)", operation, type(exc).__name__)


@router.post("")
async def join_waitlist(payload: WaitlistPayload, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    if payload.website.strip():
        return {"received": True}

    try:
        email = validate_email(payload.email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid email address.") from exc

    entry = await _get_entry(db, email)
    if entry is None:
        entry = WaitlistEntry(email=email, consented_at=utcnow())
        db.add(entry)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
        entry = await _get_entry(db, email)
        if entry is None:
            raise HTTPException(status_code=500, detail="Could not save waitlist signup.")

    changed = False
    notification_recipient = (
        settings.resend_waitlist_notification_email.strip() or settings.founder_email.strip()
    )
    if (
        entry.notification_sent_at is None
        and settings.resend_api_key.strip()
        and settings.resend_from_email.strip()
        and notification_recipient
    ):
        try:
            await _send_waitlist_notification(email)
        except (httpx.HTTPError, ResendAPIError, RuntimeError) as exc:
            _log_provider_failure("notification", exc)
        else:
            entry.notification_sent_at = utcnow()
            changed = True
    elif (
        entry.notification_sent_at is None
        and settings.resend_api_key.strip()
        and not (settings.resend_from_email.strip() and notification_recipient)
    ):
        log.warning("Waitlist notification skipped: configure RESEND_FROM_EMAIL and a notification recipient")

    if entry.resend_contact_synced_at is None and settings.resend_api_key.strip():
        try:
            await _sync_resend_contact(email)
        except (httpx.HTTPError, ResendAPIError, RuntimeError) as exc:
            _log_provider_failure("contact sync", exc)
        else:
            entry.resend_contact_synced_at = utcnow()
            changed = True

    if changed:
        await db.commit()
    return {"received": True}

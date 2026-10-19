from sqlalchemy import select

from app.database import SessionLocal
from app.models import WaitlistEntry
from app.routers import waitlist


async def test_waitlist_is_stored_when_resend_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(waitlist.settings, "resend_api_key", "")
    response = await client.post("/api/v1/waitlist", json={"email": "persist@example.com"})

    assert response.status_code == 200
    async with SessionLocal() as db:
        entry = (
            await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == "persist@example.com"))
        ).scalar_one()
    assert entry.notification_sent_at is None
    assert entry.resend_contact_synced_at is None


async def test_waitlist_persists_signup_and_sends_configured_notifications(client, monkeypatch):
    notifications = []
    contacts = []

    async def send_notification(email: str) -> None:
        notifications.append(email)

    async def sync_contact(email: str) -> None:
        contacts.append(email)

    monkeypatch.setattr(waitlist.settings, "resend_api_key", "test-send-key")
    monkeypatch.setattr(waitlist.settings, "resend_from_email", "Orqelis <updates@example.com>")
    monkeypatch.setattr(waitlist.settings, "founder_email", "owner@example.com")
    monkeypatch.setattr(waitlist, "_send_waitlist_notification", send_notification)
    monkeypatch.setattr(waitlist, "_sync_resend_contact", sync_contact)

    response = await client.post("/api/v1/waitlist", json={"email": "  Early.Access@Example.com "})

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert notifications == ["early.access@example.com"]
    assert contacts == ["early.access@example.com"]
    async with SessionLocal() as db:
        entry = (
            await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == "early.access@example.com"))
        ).scalar_one()
    assert entry.notification_sent_at is not None
    assert entry.resend_contact_synced_at is not None


async def test_resend_contact_sync_creates_global_contact(monkeypatch):
    calls = []

    async def resend_request(path: str, *, method: str = "GET", body: dict | None = None, allowed_statuses=()):
        calls.append((path, method, body, allowed_statuses))
        return type("Response", (), {"status_code": 201})()

    monkeypatch.setattr(waitlist.settings, "resend_api_key", "test-contacts-key")
    monkeypatch.setattr(waitlist, "_resend_request", resend_request)

    await waitlist._sync_resend_contact("person@example.com")

    assert calls == [("/contacts", "POST", {"email": "person@example.com", "unsubscribed": False}, (409,))]


async def test_resend_contact_sync_treats_duplicate_contact_as_already_synced(monkeypatch):
    calls = []

    async def resend_request(path: str, *, method: str = "GET", body: dict | None = None, allowed_statuses=()):
        calls.append((path, method, body, allowed_statuses))
        return type("Response", (), {"status_code": 409})()

    monkeypatch.setattr(waitlist.settings, "resend_api_key", "test-contacts-key")
    monkeypatch.setattr(waitlist, "_resend_request", resend_request)

    await waitlist._sync_resend_contact("person@example.com")

    assert calls == [("/contacts", "POST", {"email": "person@example.com", "unsubscribed": False}, (409,))]


async def test_waitlist_duplicate_does_not_duplicate_successful_notifications(client, monkeypatch):
    notifications = []

    async def send_notification(email: str) -> None:
        notifications.append(email)

    monkeypatch.setattr(waitlist.settings, "resend_api_key", "test-send-key")
    monkeypatch.setattr(waitlist.settings, "resend_from_email", "Orqelis <updates@example.com>")
    monkeypatch.setattr(waitlist.settings, "founder_email", "owner@example.com")
    monkeypatch.setattr(waitlist, "_send_waitlist_notification", send_notification)

    first = await client.post("/api/v1/waitlist", json={"email": "early@example.com"})
    second = await client.post("/api/v1/waitlist", json={"email": "EARLY@example.com"})

    assert first.status_code == second.status_code == 200
    assert notifications == ["early@example.com"]
    async with SessionLocal() as db:
        entries = (await db.execute(select(WaitlistEntry))).scalars().all()
    assert len(entries) == 1


async def test_waitlist_honeypot_is_accepted_without_storing(client):
    response = await client.post("/api/v1/waitlist", json={"email": "invalid", "website": "bot"})

    assert response.status_code == 200
    assert response.json() == {"received": True}
    async with SessionLocal() as db:
        entries = (await db.execute(select(WaitlistEntry))).scalars().all()
    assert entries == []


async def test_waitlist_rejects_invalid_email(client):
    response = await client.post("/api/v1/waitlist", json={"email": "not-an-email"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Enter a valid email address."

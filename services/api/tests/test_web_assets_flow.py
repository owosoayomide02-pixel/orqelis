"""Integration: create → verify (stub) → scan → findings with source=web_asset."""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from tests.conftest import register


@pytest.mark.asyncio
async def test_web_asset_scan_flow(client: AsyncClient):
    await register(client, "webscan@example.com", org="ScanCo")

    # Invalid domain
    bad = await client.post("/api/v1/web-assets", json={"domain": "127.0.0.1"})
    assert bad.status_code == 400

    created = await client.post("/api/v1/web-assets", json={"domain": "acme-scan.example"})
    assert created.status_code == 201, created.text
    asset = created.json()
    assert asset["verification_status"] == "unverified"
    assert "verification_instructions" in asset
    asset_id = asset["id"]

    # Scan gated until verified
    denied = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    assert denied.status_code == 403

    # Test-mode verify
    verified = await client.post(
        f"/api/v1/web-assets/{asset_id}/verify",
        headers={"X-Orqelis-Test-Verify": "1"},
    )
    assert verified.status_code == 200
    assert verified.json()["verification_status"] == "verified"

    started = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    assert started.status_code == 202, started.text
    job_id = started.json()["scan_job_id"]

    me = (await client.get("/api/v1/auth/me")).json()
    from datetime import UTC, datetime

    from sqlalchemy import delete, select

    from app.database import SessionLocal
    from app.models import ScanJob, new_id

    blocker_id = new_id()
    async with SessionLocal() as db:
        db.add(
            ScanJob(
                id=blocker_id,
                web_asset_id=asset_id,
                organization_id=me["organizations"][0]["id"],
                role="hunter",
                status="running",
                tools_run=[],
                requested_by_user_id=me["id"],
                started_at=datetime.now(UTC),
            )
        )
        await db.commit()

    again = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    assert again.status_code == 429

    async with SessionLocal() as db:
        await db.execute(delete(ScanJob).where(ScanJob.id == blocker_id))
        await db.commit()

    # Poll until original (or a later) job completes
    status = "queued"
    body: dict = {}
    for _ in range(40):
        resp = await client.get(f"/api/v1/web-assets/{asset_id}/scans/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        status = body["status"]
        if status in {"completed", "failed", "timed_out"}:
            break
        await asyncio.sleep(0.05)
    # If original finished before we blocked, start a fresh scan to assert findings
    if status != "completed":
        started2 = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
        assert started2.status_code == 202
        job_id = started2.json()["scan_job_id"]
        for _ in range(40):
            resp = await client.get(f"/api/v1/web-assets/{asset_id}/scans/{job_id}")
            body = resp.json()
            status = body["status"]
            if status in {"completed", "failed", "timed_out"}:
                break
            await asyncio.sleep(0.05)
    assert status == "completed", body

    findings = await client.get(f"/api/v1/web-assets/{asset_id}/findings")
    assert findings.status_code == 200
    rows = findings.json()
    assert len(rows) >= 1
    assert rows[0]["source"] == "web_asset"
    assert rows[0]["source_id"] == asset_id

    # Analyst / Fixer
    fid = rows[0]["id"]
    analysis = await client.post(f"/api/v1/findings/{fid}/analyze", json={})
    assert analysis.status_code == 200
    assert "explanation" in analysis.json()

    fix = await client.post(f"/api/v1/findings/{fid}/fix", json={})
    assert fix.status_code == 200
    assert fix.json()["requires_human_approval"] is True
    assert fix.json().get("applied") is False

    report = await client.post(f"/api/v1/web-assets/{asset_id}/report", json={})
    assert report.status_code == 202
    assert report.json()["report_job_id"]


@pytest.mark.asyncio
async def test_desktop_login_bearer(client: AsyncClient):
    await register(client, "desktop@example.com")
    # Clear cookie-based session by using a fresh client path — login via desktop endpoint
    resp = await client.post(
        "/api/v1/auth/desktop-login",
        json={"email": "desktop@example.com", "password": "correcthorse"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "desktop@example.com"

    refreshed = await client.post(
        "/api/v1/auth/desktop-refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

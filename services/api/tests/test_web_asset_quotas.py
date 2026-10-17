"""Server-side plan quotas for web assets and Hunter scans, plus web risk scoring."""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models import Alert
from app.scoring import compute_web_risk
from tests.conftest import register


async def _verified_asset(client: AsyncClient, domain: str) -> str:
    created = await client.post("/api/v1/web-assets", json={"domain": domain})
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    verified = await client.post(f"/api/v1/web-assets/{asset_id}/verify", headers={"X-Orqelis-Test-Verify": "1"})
    assert verified.json()["verification_status"] == "verified"
    return asset_id


async def _wait_for_scan(client: AsyncClient, asset_id: str, job_id: str) -> dict:
    body: dict = {}
    for _ in range(80):
        body = (await client.get(f"/api/v1/web-assets/{asset_id}/scans/{job_id}")).json()
        if body["status"] in {"completed", "failed", "timed_out"}:
            break
        await asyncio.sleep(0.05)
    return body


@pytest.mark.asyncio
async def test_free_tier_rejects_second_web_asset(client: AsyncClient):
    await register(client, "quota-assets@example.com", org="QuotaAssets")
    first = await client.post("/api/v1/web-assets", json={"domain": "first-quota.example"})
    assert first.status_code == 201

    again = await client.post("/api/v1/web-assets", json={"domain": "first-quota.example"})
    assert again.status_code == 201, "re-adding an existing domain stays idempotent at the limit"

    second = await client.post("/api/v1/web-assets", json={"domain": "second-quota.example"})
    assert second.status_code == 403
    assert "limit" in second.json()["detail"].lower()

    usage = (await client.get("/api/v1/web-assets/usage")).json()
    assert usage["plan_code"] == "free"
    assert usage["web_assets"] == {"used": 1, "limit": settings.web_asset_quota_free}


@pytest.mark.asyncio
async def test_paid_plan_raises_web_asset_limit(client: AsyncClient, monkeypatch):
    from app.database import SessionLocal
    from app.models import Plan, new_id
    from app.quotas import PLAN_LIMITS

    await register(client, "quota-solo@example.com", org="QuotaSolo")
    monkeypatch.setitem(PLAN_LIMITS, "quota_test", {"web_assets": 3, "scans_monthly": 25})
    async with SessionLocal() as db:
        db.add(Plan(id=new_id(), code="quota_test", name="Quota Test", description="", features_json=[]))
        await db.commit()
    activated = await client.post("/api/v1/subscription/activate", json={"plan_code": "quota_test"})
    assert activated.status_code == 200, activated.text
    for i in range(3):
        resp = await client.post("/api/v1/web-assets", json={"domain": f"p{i}-quota.example"})
        assert resp.status_code == 201, resp.text
    over = await client.post("/api/v1/web-assets", json={"domain": "p3-quota.example"})
    assert over.status_code == 403


@pytest.mark.asyncio
async def test_monthly_scan_quota_rejects_over_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "scan_quota_per_org_monthly", 1)
    await register(client, "quota-scans@example.com", org="QuotaScans")
    asset_id = await _verified_asset(client, "scans-quota.example")

    first = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    assert first.status_code == 202
    await _wait_for_scan(client, asset_id, first.json()["scan_job_id"])

    second = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    assert second.status_code == 429
    assert "quota" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_risk_score_appears_after_scan(client: AsyncClient):
    await register(client, "risk@example.com", org="RiskCo")
    asset_id = await _verified_asset(client, "risk-score.example")

    before = (await client.get(f"/api/v1/web-assets/{asset_id}")).json()
    assert before["risk_score"] is None
    assert before["has_completed_scan"] is False
    empty = await client.get(f"/api/v1/web-assets/{asset_id}/findings")
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

    started = await client.post(f"/api/v1/web-assets/{asset_id}/scan", json={"role": "hunter"})
    job = await _wait_for_scan(client, asset_id, started.json()["scan_job_id"])
    assert job["status"] == "completed", job

    after = (await client.get(f"/api/v1/web-assets/{asset_id}")).json()
    assert after["has_completed_scan"] is True
    assert after["risk_score"] >= 70, "mock scan includes a high-severity finding"

    findings = (await client.get(f"/api/v1/web-assets/{asset_id}/findings")).json()
    assert all(f["tool_source"] for f in findings)

    summary = (await client.get("/api/v1/web-assets/risk-summary")).json()
    assert summary["risk_score"] == after["risk_score"]
    assert summary["worst_asset"]["id"] == asset_id

    device_score = (await client.get("/api/v1/organizations/current/score")).json()
    assert device_score["first_run"] is True, "web findings must not leak into the endpoint score"


def test_compute_web_risk_weights():
    def alert(sev: str, risk: int) -> Alert:
        return Alert(severity=sev, risk_score=risk, status="open")

    assert compute_web_risk(alerts=[], scanned=False)["risk_score"] is None
    assert compute_web_risk(alerts=[], scanned=True)["risk_score"] == 0
    result = compute_web_risk(alerts=[alert("medium", 40), alert("high", 70), alert("medium", 40)], scanned=True)
    assert result["risk_score"] == 72
    assert result["by_severity"]["medium"] == 2
    capped = compute_web_risk(alerts=[alert("critical", 90)] * 5, scanned=True)
    assert capped["risk_score"] == 100

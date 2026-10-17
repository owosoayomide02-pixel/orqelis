"""Regressions for web-asset endpoints: SQLite naive datetimes and free-form LLM confidence values."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.routers.web_assets import _confidence
from tests.conftest import register


@pytest.mark.asyncio
async def test_repeat_verify_is_rate_limited_not_500(client: AsyncClient):
    await register(client, "verify-repeat@example.com", org="VerifyRepeat")
    created = await client.post("/api/v1/web-assets", json={"domain": "verify-repeat.example"})
    asset_id = created.json()["id"]

    first = await client.post(f"/api/v1/web-assets/{asset_id}/verify")
    assert first.status_code == 200, first.text

    again = await client.post(f"/api/v1/web-assets/{asset_id}/verify")
    assert again.status_code == 429, again.text
    assert "retrying verification" in again.json()["detail"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0.72, 0.72),
        (85, 0.85),
        ("85%", 0.85),
        ("0.4", 0.4),
        ("High", 0.85),
        ("very low", 0.15),
        ("certain-ish", 0.5),
        (None, 0.5),
        (True, 0.5),
        (-3, 0.0),
    ],
)
def test_confidence_coercion(raw, expected):
    assert _confidence(raw) == pytest.approx(expected)

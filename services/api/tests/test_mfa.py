from tests.conftest import register
import pyotp


async def test_mfa_setup_enable_and_login(client):
    await register(client, "mfa@example.com")
    setup = await client.post("/api/v1/auth/mfa/setup")
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    bad = await client.post("/api/v1/auth/mfa/enable", json={"code": "000000"})
    assert bad.status_code == 400
    enabled = await client.post("/api/v1/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()})
    assert enabled.status_code == 200
    await client.post("/api/v1/auth/logout")
    first = await client.post("/api/v1/auth/login", json={"email": "mfa@example.com", "password": "correcthorse"})
    assert first.status_code == 200
    assert first.json()["mfa_required"] is True
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401
    second = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@example.com", "password": "correcthorse", "totp": pyotp.TOTP(secret).now()},
    )
    assert second.status_code == 200
    assert second.json()["mfa_required"] is False
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["mfa_enabled"] is True

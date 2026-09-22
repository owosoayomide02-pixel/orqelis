from tests.conftest import register


async def test_tenant_isolation(client):
    await register(client, "a@example.com", "Alpha")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    assert enroll.status_code == 200
    code = enroll.json()["code"]
    await client.post("/api/v1/auth/logout")

    enrolled = await client.post(
        "/api/v1/agent/enroll",
        json={"code": code, "hostname": "ALPHA-PC", "os_name": "Windows"},
    )
    assert enrolled.status_code == 200
    token = enrolled.json()["device_token"]
    events = await client.post(
        "/api/v1/agent/events",
        headers={"X-Orqelis-Device-Token": token},
        json={
            "events": [
                {"category": "authentication", "event_type": "auth_failure", "payload": {"user": "admin"}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {"user": "admin"}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {"user": "admin"}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {"user": "admin"}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {"user": "admin"}},
            ]
        },
    )
    assert events.status_code == 200
    assert events.json()["alerts"] >= 1

    await register(client, "b@example.com", "Beta")
    alerts = await client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    assert alerts.json() == []
    devices = await client.get("/api/v1/devices")
    assert devices.json() == []


async def test_user_cookie_cannot_call_agent_ingest(client):
    await register(client, "user@example.com")
    response = await client.post("/api/v1/agent/events", json={"events": []})
    assert response.status_code == 401


async def test_device_token_cannot_call_user_api(client):
    await register(client, "owner2@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    code = enroll.json()["code"]
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": code, "hostname": "PC"})
    token = enrolled.json()["device_token"]
    await client.post("/api/v1/auth/logout")
    response = await client.get("/api/v1/alerts", headers={"X-Orqelis-Device-Token": token})
    assert response.status_code == 401

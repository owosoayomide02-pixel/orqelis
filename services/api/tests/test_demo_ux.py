from tests.conftest import register


async def test_register_returns_dev_verification_url(client):
    data = await register(client, "verifyux@example.com")
    assert data["verification_url"].startswith("http://localhost:3000/verify-email?token=")
    me = await client.get("/api/v1/auth/me")
    assert me.json()["dev_email_links"] is True
    link = await client.post("/api/v1/auth/verification-link")
    assert link.status_code == 200
    assert "token=" in link.json()["verification_url"]


async def test_demo_load_is_labeled_and_refuses_live_mix(client):
    await register(client, "demo@example.com")
    loaded = await client.post("/api/v1/demo/load")
    assert loaded.status_code == 200
    assert "LABELED DEMO" in loaded.json()["label"]
    org = await client.get("/api/v1/organizations/current")
    assert org.json()["demo"] is True
    alerts = await client.get("/api/v1/alerts?severity=critical&status=open")
    assert alerts.status_code == 200
    assert any(row["detection_source"] == "demo" for row in alerts.json())
    again = await client.post("/api/v1/demo/load")
    assert again.status_code == 200
    assert again.json()["already_loaded"] is True
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    blocked = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "REAL-PC"})
    assert blocked.status_code == 409


async def test_demo_refuses_when_live_device_exists(client):
    await register(client, "live@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    live = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "FIN-PC"})
    assert live.status_code == 200
    demo = await client.post("/api/v1/demo/load")
    assert demo.status_code == 409

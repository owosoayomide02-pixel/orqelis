from app.config import settings
from tests.conftest import register


async def test_high_alert_gets_auto_sentinel_analysis(client):
    await register(client, "autoai@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "PC"})
    await client.post(
        "/api/v1/agent/events",
        headers={"X-Orqelis-Device-Token": enrolled.json()["device_token"]},
        json={"events": [{"category": "windows_security", "event_type": "privileged_account_created", "payload": {}}]},
    )
    alerts = (await client.get("/api/v1/alerts")).json()
    assert alerts
    high = next(row for row in alerts if row["severity"] in {"high", "critical"})
    analyses = (await client.get(f"/api/v1/ai/analyses?subject_id={high['id']}")).json()
    assert any(item["role"] == "sentinel" for item in analyses)


async def test_agent_download_catalog(client):
    await register(client, "dl@example.com")
    pack = await client.get("/api/v1/devices/agent-downloads")
    assert pack.status_code == 200
    rows = pack.json()["platforms"]
    platforms = {row["platform"] for row in rows}
    assert platforms == {"windows", "macos", "linux"}
    assert all(settings.resolved_public_api_url in row["enroll_commands"] for row in rows)
    missing = await client.get("/api/v1/devices/agent-downloads/windows")
    assert missing.status_code in {200, 404}


async def test_report_includes_score_and_alerts(client):
    await register(client, "report@example.com")
    report = await client.post("/api/v1/reports")
    assert report.status_code == 200
    body = report.json()["body_markdown"]
    assert "Security Score" in body
    assert "Sentinel analyses" in body

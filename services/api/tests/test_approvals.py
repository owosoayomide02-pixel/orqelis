from tests.conftest import register


async def test_recommend_and_approve_refresh_policy(client):
    await register(client, "ops@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "FIN-PC"})
    device_id = enrolled.json()["device_id"]
    rec = await client.post(
        "/api/v1/actions/recommend",
        json={"device_id": device_id, "kind": "refresh_policy", "reason": "Apply latest collection policy"},
    )
    assert rec.status_code == 200
    approval_id = rec.json()["approval_id"]
    decided = await client.post(f"/api/v1/approvals/{approval_id}/decide", json={"decision": "approve"})
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    heartbeat = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-Orqelis-Device-Token": enrolled.json()["device_token"]},
        json={"health": {}, "posture": {}},
    )
    assert heartbeat.status_code == 200
    kinds = {item["kind"] for item in heartbeat.json()["commands"]}
    assert "refresh_policy" in kinds


async def test_ai_analysis_heuristic(client):
    await register(client, "analyst@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "PC"})
    await client.post(
        "/api/v1/agent/events",
        headers={"X-Orqelis-Device-Token": enrolled.json()["device_token"]},
        json={
            "events": [
                {"category": "authentication", "event_type": "auth_failure", "payload": {}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {}},
                {"category": "authentication", "event_type": "auth_failure", "payload": {}},
            ]
        },
    )
    alerts = (await client.get("/api/v1/alerts")).json()
    assert alerts
    analysis = await client.post(
        "/api/v1/ai/analyze",
        json={"role": "analyst", "subject_type": "alert", "subject_id": alerts[0]["id"]},
    )
    assert analysis.status_code == 200
    assert analysis.json()["provider"] == "heuristic"
    assert "explanation" in analysis.json()["output"]

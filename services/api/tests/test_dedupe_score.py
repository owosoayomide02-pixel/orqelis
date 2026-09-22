from tests.conftest import register


async def _enroll(client):
    await register(client, "dedupe@example.com")
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "PC"})
    return enrolled.json()["device_token"]


def _burst():
    return {
        "events": [
            {"category": "authentication", "event_type": "auth_failure", "payload": {}},
            {"category": "authentication", "event_type": "auth_failure", "payload": {}},
            {"category": "authentication", "event_type": "auth_failure", "payload": {}},
            {"category": "authentication", "event_type": "auth_failure", "payload": {}},
            {"category": "authentication", "event_type": "auth_failure", "payload": {}},
        ]
    }


async def test_duplicate_rule_does_not_create_second_open_alert(client):
    token = await _enroll(client)
    headers = {"X-Orqelis-Device-Token": token}
    first = await client.post("/api/v1/agent/events", headers=headers, json=_burst())
    second = await client.post("/api/v1/agent/events", headers=headers, json=_burst())
    assert first.status_code == 200
    assert second.status_code == 200
    alerts = (await client.get("/api/v1/alerts")).json()
    open_auth = [row for row in alerts if row["rule_id"] == "auth_fail_burst" and row["status"] == "open"]
    assert len(open_auth) == 1


async def test_security_score_endpoint(client):
    await register(client, "score@example.com")
    empty = await client.get("/api/v1/organizations/current/score")
    assert empty.status_code == 200
    assert empty.json()["first_run"] is True
    assert empty.json()["score"] is None
    enroll = await client.post("/api/v1/devices/enrollments", json={})
    enrolled = await client.post("/api/v1/agent/enroll", json={"code": enroll.json()["code"], "hostname": "PC"})
    await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-Orqelis-Device-Token": enrolled.json()["device_token"]},
        json={"health": {"can_read_security_log": True}, "posture": {"defender_status": "on", "firewall_status": "on"}},
    )
    scored = await client.get("/api/v1/organizations/current/score")
    assert scored.json()["first_run"] is False
    assert scored.json()["score"] >= 80

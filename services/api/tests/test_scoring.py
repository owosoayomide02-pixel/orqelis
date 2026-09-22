from datetime import UTC, datetime, timedelta

from app.models import Alert, Device, Vulnerability, new_id
from app.scoring import compute_score, posture_checklist


def _device(**kwargs) -> Device:
    now = datetime.now(UTC)
    data = dict(
        id=new_id(),
        organization_id="org",
        name="PC",
        hostname="PC",
        status="online",
        last_seen_at=now,
        health_json={"can_read_security_log": True},
        posture_json={"defender_status": "on", "firewall_status": "on"},
    )
    data.update(kwargs)
    return Device(**data)


def test_first_run_has_no_fake_score():
    result = compute_score(devices=[], alerts=[], incidents=[], vulnerabilities=[])
    assert result["first_run"] is True
    assert result["score"] is None


def test_healthy_org_scores_high():
    result = compute_score(devices=[_device()], alerts=[], incidents=[], vulnerabilities=[])
    assert result["score"] == 100
    assert result["drivers"] == []


def test_defender_off_and_critical_alert_reduce_score():
    device = _device(posture_json={"defender_status": "off", "firewall_status": "on"})
    alert = Alert(
        id=new_id(),
        organization_id="org",
        device_id=device.id,
        title="Critical",
        severity="critical",
        status="open",
        rule_id="x",
    )
    result = compute_score(devices=[device], alerts=[alert], incidents=[], vulnerabilities=[])
    assert result["score"] < 70
    reasons = " ".join(item["reason"] for item in result["drivers"])
    assert "protection off" in reasons.lower() or "Critical" in reasons


def test_offline_device_is_a_driver():
    device = _device(last_seen_at=datetime.now(UTC) - timedelta(hours=3), status="offline")
    result = compute_score(devices=[device], alerts=[], incidents=[], vulnerabilities=[])
    assert result["score"] < 100
    assert any("offline" in item["reason"] for item in result["drivers"])


def test_linux_na_protection_does_not_penalize():
    device = _device(posture_json={"defender_status": "n/a", "firewall_status": "on"})
    result = compute_score(devices=[device], alerts=[], incidents=[], vulnerabilities=[])
    assert result["score"] == 100


def test_posture_checklist_flags_firewall_off():
    device = _device(posture_json={"defender_status": "on", "firewall_status": "off"})
    items = {row["id"]: row for row in posture_checklist(device, high_open_alerts=2)}
    assert items["firewall"]["ok"] is False
    assert items["no_high_alerts"]["ok"] is False
    assert items["agent_online"]["ok"] is True

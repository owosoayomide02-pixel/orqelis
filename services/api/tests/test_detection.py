from orqelis_detection.engine import DetectionEngine


def test_repeated_auth_failures():
    engine = DetectionEngine()
    events = [
        {"id": str(i), "device_id": "d1", "event_type": "auth_failure", "category": "authentication"}
        for i in range(6)
    ]
    findings = engine.analyze(events)
    assert any(item.rule_id == "auth_fail_burst" for item in findings)


def test_fail_then_success_and_correlation():
    engine = DetectionEngine()
    events = [
        {"id": "1", "device_id": "d1", "event_type": "auth_failure", "category": "authentication", "occurred_at": "2026-01-01T00:00:01"},
        {"id": "2", "device_id": "d1", "event_type": "auth_failure", "category": "authentication", "occurred_at": "2026-01-01T00:00:02"},
        {"id": "3", "device_id": "d1", "event_type": "auth_failure", "category": "authentication", "occurred_at": "2026-01-01T00:00:03"},
        {"id": "4", "device_id": "d1", "event_type": "auth_success", "category": "authentication", "occurred_at": "2026-01-01T00:00:04"},
        {
            "id": "5",
            "device_id": "d1",
            "event_type": "snapshot",
            "category": "process",
            "payload": {"cmdline": "powershell -enc QQBB", "path": "C:\\Windows\\Temp\\a.exe"},
        },
    ]
    findings = engine.analyze(events)
    incidents = engine.correlate(findings)
    assert incidents
    assert incidents[0]["severity"] in {"high", "critical"}


def test_defender_disabled_is_posture_finding():
    engine = DetectionEngine()
    findings = engine.analyze(
        [
            {
                "device_id": "d1",
                "category": "security_control",
                "event_type": "posture",
                "payload": {"defender_status": "off", "firewall_status": "on"},
            }
        ]
    )
    match = next(item for item in findings if item.rule_id == "defender_disabled")
    assert match.finding_type == "vulnerability"
    assert match.severity == "critical"

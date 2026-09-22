from orqelis_detection.engine import DetectionEngine


def test_linux_firewall_off_is_not_windows_titled():
    engine = DetectionEngine()
    findings = engine.analyze(
        [
            {
                "category": "security_control",
                "payload": {"platform": "linux", "defender_status": "n/a", "firewall_status": "off"},
            }
        ]
    )
    titles = [item.title for item in findings]
    assert any("Linux host firewall" in title for title in titles)
    assert not any("Windows Firewall" in title for title in titles)
    assert not any("Defender" in title for title in titles)


def test_macos_gatekeeper_off():
    engine = DetectionEngine()
    findings = engine.analyze(
        [
            {
                "category": "security_control",
                "payload": {"platform": "darwin", "defender_status": "off", "firewall_status": "on"},
            }
        ]
    )
    assert any("Gatekeeper" in item.title for item in findings)

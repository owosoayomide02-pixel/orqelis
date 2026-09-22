from pathlib import Path


def test_agent_notice_mentions_authorization():
    text = (Path(__file__).resolve().parents[1] / "orqelis_agent" / "cli.py").read_text(encoding="utf-8")
    assert "authorized" in text.lower()
    assert "telemetry" in text.lower()

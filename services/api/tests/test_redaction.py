from orqelis_security.redaction import redact_mapping


def test_redaction_strips_secrets_and_emails():
    data = redact_mapping({"api_key": "sk-test", "note": "contact person@example.com", "nested": {"password": "x"}})
    assert data["api_key"] == "[redacted]"
    assert data["nested"]["password"] == "[redacted]"
    assert "[redacted-email]" in data["note"]

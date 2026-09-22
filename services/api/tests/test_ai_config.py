from app.config import resolve_ai_provider


def test_no_key_stays_heuristic():
    assert resolve_ai_provider(provider="groq", api_key="", openai_api_key="") == "heuristic"


def test_groq_key_keeps_groq_provider():
    assert resolve_ai_provider(provider="groq", api_key="gsk_test", openai_api_key="") == "groq"


def test_key_without_provider_uses_openai_compatible():
    assert resolve_ai_provider(provider="heuristic", api_key="sk-test", openai_api_key="") == "openai"

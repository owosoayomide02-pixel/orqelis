from app.config import resolve_ai_key, resolve_ai_provider


def test_no_key_stays_heuristic():
    assert resolve_ai_provider(provider="groq", api_key="", openai_api_key="") == "heuristic"


def test_groq_key_keeps_groq_provider():
    assert resolve_ai_provider(provider="groq", api_key="gsk_test", openai_api_key="") == "groq"


def test_anthropic_key_keeps_anthropic_provider():
    assert resolve_ai_provider(provider="anthropic", api_key="anthropic-test", openai_api_key="") == "anthropic"


def test_key_without_provider_uses_openai_compatible():
    assert resolve_ai_provider(provider="heuristic", api_key="sk-test", openai_api_key="") == "openai"


def test_explicit_openai_provider_prefers_openai_key():
    assert resolve_ai_key(provider="openai", api_key="groq-test", openai_api_key="openai-test") == "openai-test"

def test_whitespace_generic_key_does_not_hide_openai_key():
    assert resolve_ai_provider(provider="heuristic", api_key="  ", openai_api_key="openai-test") == "openai"
    assert resolve_ai_key(provider="openai", api_key="  ", openai_api_key="openai-test") == "openai-test"


def test_groq_provider_keeps_generic_key():
    assert resolve_ai_key(provider="groq", api_key="groq-test", openai_api_key="openai-test") == "groq-test"


def test_gemini_key_selects_gemini_when_openai_is_not_configured():
    assert resolve_ai_provider(provider="heuristic", api_key="", gemini_api_key="gemini-test") == "gemini"
    assert resolve_ai_key(provider="gemini", api_key="", gemini_api_key="gemini-test") == "gemini-test"


def test_openai_remains_default_when_both_provider_keys_are_configured():
    assert (
        resolve_ai_provider(
            provider="heuristic",
            api_key="",
            openai_api_key="openai-test",
            gemini_api_key="gemini-test",
        )
        == "openai"
    )


def test_explicit_gemini_provider_uses_gemini_key():
    assert (
        resolve_ai_key(
            provider="gemini",
            api_key="",
            openai_api_key="openai-test",
            gemini_api_key="gemini-test",
        )
        == "gemini-test"
    )


def test_openrouter_key_selects_openrouter_when_no_other_provider_key_exists():
    assert (
        resolve_ai_provider(
            provider="heuristic",
            api_key="",
            openrouter_api_key="openrouter-test",
        )
        == "openrouter"
    )


def test_explicit_openrouter_provider_uses_its_own_key():
    assert (
        resolve_ai_key(
            provider="openrouter",
            api_key="",
            openai_api_key="openai-test",
            openrouter_api_key="openrouter-test",
        )
        == "openrouter-test"
    )


def test_nvidia_key_selects_nvidia_when_provider_is_automatic():
    assert (
        resolve_ai_provider(
            provider="heuristic",
            api_key="",
            nvidia_api_key="nvidia-test",
        )
        == "nvidia"
    )


def test_explicit_nvidia_provider_uses_its_own_key():
    assert (
        resolve_ai_key(
            provider="nvidia",
            api_key="",
            openai_api_key="openai-test",
            nvidia_api_key="nvidia-test",
        )
        == "nvidia-test"
    )

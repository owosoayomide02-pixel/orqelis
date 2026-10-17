from __future__ import annotations

import json

from orqelis_ai.gateway import AIGateway


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "content": [{"type": "text", "text": '{"explanation":"Reviewed safely.","confidence":0.82}'}],
            "usage": {"input_tokens": 35, "output_tokens": 12},
        }


class OpenAICompatibleResponse(FakeResponse):
    def json(self) -> dict:
        return {
            "choices": [
                {"message": {"content": '{"explanation":"Reviewed safely.","confidence":0.82}'}}
            ],
            "usage": {"prompt_tokens": 35, "completion_tokens": 12},
        }


def test_anthropic_messages_api_uses_redacted_role_payload(monkeypatch):
    captured: dict = {}

    def fake_post(_client, url, *, headers, json: dict):
        captured.update(url=url, headers=headers, body=json)
        return FakeResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(provider="anthropic", api_key="test-key", model="claude-test")

    result = gateway.analyze(
        role="analyst",
        subject_type="finding",
        payload={"title": "Expired certificate", "severity": "high", "api_key": "secret-value"},
    )

    assert result.provider == "anthropic"
    assert result.model == "claude-test"
    assert result.output["explanation"] == "Reviewed safely."
    assert result.prompt_tokens == 35
    assert result.completion_tokens == 12
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"]["messages"][0]["role"] == "user"
    assert "secret-value" not in json.dumps(captured["body"])


def test_anthropic_requires_explicit_model_and_falls_back(monkeypatch):
    gateway = AIGateway(provider="anthropic", api_key="test-key", model="")
    result = gateway.analyze(role="analyst", subject_type="finding", payload={"title": "Test finding"})

    assert result.provider == "heuristic"
    assert result.output["fallback"] is True
    assert result.output["analysis_unavailable"] is True
    assert "AI_MODEL" in result.output["provider_error"]


def test_gemini_generate_content_uses_api_key_header_and_redacted_payload(monkeypatch):
    captured: dict = {}

    class GeminiResponse(FakeResponse):
        def json(self) -> dict:
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"explanation":"Reviewed safely.","confidence":0.82}'}]}}
                ],
                "usageMetadata": {"promptTokenCount": 35, "candidatesTokenCount": 12},
            }

    def fake_post(_client, url, *, headers, json: dict):
        captured.update(url=url, headers=headers, body=json)
        return GeminiResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(provider="gemini", api_key="gemini-test")

    result = gateway.analyze(
        role="analyst",
        subject_type="finding",
        payload={"title": "Expired certificate", "severity": "high", "api_key": "secret-value"},
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-2.5-flash"
    assert result.output["explanation"] == "Reviewed safely."
    assert result.prompt_tokens == 35
    assert result.completion_tokens == 12
    assert captured["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "gemini-test"
    assert "secret-value" not in json.dumps(captured["body"])


def test_openai_failure_falls_back_to_gemini(monkeypatch):
    requested_urls: list[str] = []

    class GeminiResponse(FakeResponse):
        def json(self) -> dict:
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"explanation":"Gemini reviewed it.","confidence":0.7}'}]}}
                ],
                "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 8},
            }

    def fake_post(_client, url, *, headers, json: dict):
        requested_urls.append(url)
        if "chat/completions" in url:
            raise RuntimeError("OpenAI unavailable")
        return GeminiResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(
        provider="openai",
        api_key="openai-test",
        fallback_provider="gemini",
        fallback_api_key="gemini-test",
    )

    result = gateway.analyze(role="analyst", subject_type="finding", payload={"title": "Test finding"})

    assert result.provider == "gemini"
    assert result.output["provider_fallback"] == "openai -> gemini"
    assert len(requested_urls) == 3
    assert requested_urls[-1].endswith("/models/gemini-2.5-flash:generateContent")


def test_openrouter_uses_openai_compatible_api(monkeypatch):
    captured: dict = {}

    def fake_post(_client, url, *, headers, json: dict):
        captured.update(url=url, headers=headers, body=json)
        return OpenAICompatibleResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(provider="openrouter", api_key="openrouter-test")

    result = gateway.analyze(role="analyst", subject_type="finding", payload={"title": "Test finding"})

    assert result.provider == "openrouter"
    assert result.model == "openai/gpt-4o-mini"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer openrouter-test"
    assert captured["headers"]["HTTP-Referer"] == "https://orqelis.com"
    assert captured["headers"]["X-Title"] == "Orqelis"
    assert captured["body"]["model"] == "openai/gpt-4o-mini"


def test_nvidia_uses_nim_openai_compatible_api(monkeypatch):
    captured: dict = {}

    def fake_post(_client, url, *, headers, json: dict):
        captured.update(url=url, headers=headers, body=json)
        return OpenAICompatibleResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(provider="nvidia", api_key="nvidia-test")

    result = gateway.analyze(role="analyst", subject_type="finding", payload={"title": "Test finding"})

    assert result.provider == "nvidia"
    assert result.model == "meta/llama-3.3-70b-instruct"
    assert captured["url"] == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer nvidia-test"
    assert captured["body"]["model"] == "meta/llama-3.3-70b-instruct"


def test_nvidia_without_key_uses_configured_openrouter_fallback(monkeypatch):
    captured: dict = {}

    def fake_post(_client, url, *, headers, json: dict):
        captured.update(url=url, headers=headers, body=json)
        return OpenAICompatibleResponse()

    monkeypatch.setattr("orqelis_ai.gateway.httpx.Client.post", fake_post)
    gateway = AIGateway(
        provider="nvidia",
        fallback_provider="openrouter",
        fallback_api_key="openrouter-test",
    )

    result = gateway.analyze(role="analyst", subject_type="finding", payload={"title": "Test finding"})

    assert result.provider == "openrouter"
    assert result.output["provider_fallback"] == "nvidia -> openrouter"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"

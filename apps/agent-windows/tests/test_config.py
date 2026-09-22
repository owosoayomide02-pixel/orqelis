from orqelis_agent.config import AgentConfig, default_api_url


def test_default_api_url_uses_orqelis_env(monkeypatch):
    monkeypatch.setenv("ORQELIS_API_URL", "https://api.orqelis.example/")
    monkeypatch.delenv("DEVICE_AGENT_API_URL", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_API_URL", raising=False)
    assert default_api_url() == "https://api.orqelis.example"


def test_empty_config_uses_default(monkeypatch):
    monkeypatch.setenv("ORQELIS_API_URL", "https://api.orqelis.example")
    assert AgentConfig().api_url == "https://api.orqelis.example"

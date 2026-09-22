from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def config_path() -> Path:
    root = Path.home() / ".orqelis"
    root.mkdir(parents=True, exist_ok=True)
    return root / "agent.json"


def default_api_url() -> str:
    return (
        os.environ.get("ORQELIS_API_URL")
        or os.environ.get("DEVICE_AGENT_API_URL")
        or os.environ.get("NEXT_PUBLIC_API_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")


@dataclass
class AgentConfig:
    api_url: str = ""
    device_id: str = ""
    device_token: str = ""

    def __post_init__(self) -> None:
        if not self.api_url:
            self.api_url = default_api_url()


def load_config() -> AgentConfig:
    path = config_path()
    if not path.exists():
        return AgentConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentConfig(**{k: data.get(k, "") for k in ("api_url", "device_id", "device_token")})


def save_config(config: AgentConfig) -> None:
    config_path().write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")

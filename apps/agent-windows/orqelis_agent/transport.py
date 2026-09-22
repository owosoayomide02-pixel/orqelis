from __future__ import annotations

import time
from typing import Any

import httpx

from orqelis_agent.config import AgentConfig


class AgentClient:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.device_token:
            headers["X-Orqelis-Device-Token"] = self.config.device_token
        return headers

    def _json(self, method: str, path: str, *, json: dict[str, Any] | None = None, timeout: float = 20.0) -> dict[str, Any]:
        last: Exception | None = None
        url = f"{self.config.api_url}{path}"
        for delay in (0.0, 1.0, 3.0):
            if delay:
                time.sleep(delay)
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.request(method, url, headers=self._headers(), json=json)
                if response.status_code >= 500:
                    last = RuntimeError(f"server {response.status_code}")
                    continue
                response.raise_for_status()
                return response.json() if response.content else {}
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None and exc.response.status_code < 500:
                    raise
        if last:
            raise last
        return {}

    def enroll(self, code: str) -> dict[str, Any]:
        import platform
        import socket

        body = {
            "code": code.strip(),
            "hostname": socket.gethostname(),
            "os_name": platform.system(),
            "os_version": platform.version(),
            "agent_version": "0.1.0",
        }
        return self._json("POST", "/api/v1/agent/enroll", json=body)

    def heartbeat(self) -> dict[str, Any]:
        from orqelis_agent.collect import health, posture

        return self._json(
            "POST",
            "/api/v1/agent/heartbeat",
            json={"health": health(), "posture": posture()},
        )

    def send_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        return self._json("POST", "/api/v1/agent/events", json={"events": events}, timeout=30.0)

    def ack(self, command_ids: list[str]) -> None:
        self._json("POST", "/api/v1/agent/commands/ack", json={"command_ids": command_ids})

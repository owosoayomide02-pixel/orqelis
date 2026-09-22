from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
SECRET_KEYS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
}


def redact_text(value: str) -> str:
    value = EMAIL_RE.sub("[redacted-email]", value)
    value = IPV4_RE.sub("[redacted-ip]", value)
    return value


def redact_mapping(data: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            lowered = str(key).lower()
            if lowered in SECRET_KEYS or "password" in lowered or lowered.endswith("_key"):
                out[key] = "[redacted]"
            else:
                out[key] = redact_mapping(value, depth=depth + 1)
        return out
    if isinstance(data, list):
        return [redact_mapping(item, depth=depth + 1) for item in data[:50]]
    if isinstance(data, str):
        return redact_text(data)
    return data

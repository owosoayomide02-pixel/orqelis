from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

AGENT_VERSION = "0.1.0"


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def event(category: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": category,
        "event_type": event_type,
        "occurred_at": utcnow(),
        "payload": payload,
    }

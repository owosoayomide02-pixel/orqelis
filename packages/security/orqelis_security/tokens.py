from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any

import jwt


def new_secret(nbytes: int = 32) -> str:
    return token_urlsafe(nbytes)


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def create_token(
    subject: str,
    secret: str,
    *,
    minutes: int = 60,
    token_type: str = "access",
    extra: dict[str, Any] | None = None,
    algorithm: str = "HS256",
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, *, algorithms: list[str] | None = None) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=algorithms or ["HS256"])

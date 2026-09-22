from __future__ import annotations

import base64
import hashlib


def seal(plaintext: str, key: str) -> str:
    material = hashlib.sha256((key or "orqelis-dev-key").encode("utf-8")).digest()
    data = (plaintext or "").encode("utf-8")
    sealed = bytes(byte ^ material[index % len(material)] for index, byte in enumerate(data))
    return base64.urlsafe_b64encode(sealed).decode("ascii")


def unseal(token: str, key: str) -> str:
    material = hashlib.sha256((key or "orqelis-dev-key").encode("utf-8")).digest()
    try:
        data = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception:
        return ""
    plain = bytes(byte ^ material[index % len(material)] for index, byte in enumerate(data))
    return plain.decode("utf-8", errors="ignore")

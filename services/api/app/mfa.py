from __future__ import annotations

import pyotp

from app.config import settings
from orqelis_security.crypto import seal, unseal


def new_totp_secret() -> str:
    return pyotp.random_base32()


def otpauth_url(email: str, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Orqelis")


def encrypt_secret(secret: str) -> str:
    return seal(secret, settings.encryption_key or settings.jwt_secret)


def decrypt_secret(token: str) -> str:
    return unseal(token, settings.encryption_key or settings.jwt_secret)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)

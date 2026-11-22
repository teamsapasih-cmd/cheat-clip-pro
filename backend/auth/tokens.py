"""Password hashing and signed access-token primitives.

This module does not create routes or issue tokens until an application layer
has verified the user record and account status.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    return _password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return _password_hash.verify(password, encoded_hash)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: int = 30) -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters")
    if not subject:
        raise ValueError("Token subject is required")
    if not 1 <= expires_minutes <= 1440:
        raise ValueError("Token lifetime must be between 1 and 1440 minutes")

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            return None
        return payload
    except JWTError:
        return None

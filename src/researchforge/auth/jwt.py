"""JWT token creation and verification."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt

_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
_ALGORITHM = "HS256"
_EXPIRY_HOURS = 72


def create_access_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": datetime.now(UTC) + timedelta(hours=_EXPIRY_HOURS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, str] | None:
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return {
            "sub": str(payload["sub"]),
            "email": str(payload.get("email", "")),
            "name": str(payload.get("name", "")),
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

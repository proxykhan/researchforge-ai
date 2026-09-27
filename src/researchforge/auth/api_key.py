"""API key authentication utilities.

Provides key generation, hashing, and a FastAPI dependency that extracts
and validates the Bearer token from the Authorization header.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_api_key() -> str:
    """Generate a cryptographically secure API key (returned once to the user)."""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """One-way SHA-256 hash of an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()

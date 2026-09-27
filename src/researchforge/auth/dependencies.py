"""FastAPI authentication dependencies.

The ``AuthDependency`` extracts the Bearer token from the Authorization
header, hashes it, and looks up the corresponding user.
When auth is disabled (development/testing), it returns a sentinel user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from researchforge.auth.api_key import hash_api_key


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents the current authenticated API user."""

    id: str
    email: str
    name: str


class UserLookup(Protocol):
    """Looks up a user by their hashed API key."""

    async def find_by_key_hash(self, key_hash: str) -> AuthenticatedUser | None: ...


_ANONYMOUS = AuthenticatedUser(id="anonymous", email="", name="anonymous")


class AuthDependency:
    """Callable FastAPI dependency for API key authentication.

    When ``enabled=False``, all requests get the anonymous sentinel user.
    """

    def __init__(self, user_lookup: UserLookup, *, enabled: bool = True) -> None:
        self._lookup = user_lookup
        self._enabled = enabled

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = None,
    ) -> AuthenticatedUser:
        if not self._enabled:
            return _ANONYMOUS

        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        key_hash = hash_api_key(credentials.credentials)
        user = await self._lookup.find_by_key_hash(key_hash)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

"""UserLookup implementations for API key authentication."""

from __future__ import annotations

from researchforge.auth.dependencies import AuthenticatedUser


class InMemoryUserStore:
    """Dict-backed user store for testing."""

    def __init__(self) -> None:
        self._users_by_hash: dict[str, AuthenticatedUser] = {}

    def add_user(self, key_hash: str, user: AuthenticatedUser) -> None:
        self._users_by_hash[key_hash] = user

    async def find_by_key_hash(self, key_hash: str) -> AuthenticatedUser | None:
        return self._users_by_hash.get(key_hash)

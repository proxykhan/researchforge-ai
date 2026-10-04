"""PostgreSQL-backed user store for JWT authentication."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from researchforge.auth.dependencies import AuthenticatedUser
from researchforge.auth.passwords import hash_password, verify_password
from researchforge.database.models import UserRow


class PostgresUserStore:
    """Manages users in PostgreSQL — registration, login, and lookup."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create_user(self, email: str, name: str, password: str) -> AuthenticatedUser:
        user_id = str(uuid.uuid4())
        pw_hash = hash_password(password)
        async with self._sf() as session, session.begin():
            row = UserRow(id=user_id, email=email, name=name, password_hash=pw_hash)
            session.add(row)
        return AuthenticatedUser(id=user_id, email=email, name=name)

    async def authenticate(self, email: str, password: str) -> AuthenticatedUser | None:
        async with self._sf() as session:
            stmt = select(UserRow).where(
                func.lower(UserRow.email) == email.strip().lower(), UserRow.is_active.is_(True)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None or not verify_password(password, row.password_hash):
                return None
            return AuthenticatedUser(id=row.id, email=row.email, name=row.name)

    async def get_by_id(self, user_id: str) -> AuthenticatedUser | None:
        async with self._sf() as session:
            row = await session.get(UserRow, user_id)
            if row is None or not row.is_active:
                return None
            return AuthenticatedUser(id=row.id, email=row.email, name=row.name)

    async def email_exists(self, email: str) -> bool:
        async with self._sf() as session:
            stmt = select(UserRow.id).where(func.lower(UserRow.email) == email.strip().lower())
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def find_by_key_hash(self, key_hash: str) -> AuthenticatedUser | None:
        async with self._sf() as session:
            stmt = select(UserRow).where(
                UserRow.api_key_hash == key_hash, UserRow.is_active.is_(True)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return AuthenticatedUser(id=row.id, email=row.email, name=row.name)

"""Email matching for login/registration must ignore case and surrounding spaces.

The PostgreSQL tests run in CI's integration job (DATABASE_URL set) and skip elsewhere.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from researchforge.api.routes.auth import LoginRequest, RegisterRequest
from researchforge.auth.passwords import hash_password
from researchforge.auth.postgres_user_store import PostgresUserStore
from researchforge.config import load_settings
from researchforge.database.engine import build_engine, build_session_factory
from researchforge.database.models import Base, UserRow


class TestRequestNormalization:
    def test_login_email_is_trimmed_and_lowercased(self):
        body = LoginRequest(email="  Khan.Test@Gmail.com ", password="x")
        assert body.email == "khan.test@gmail.com"

    def test_register_email_is_trimmed_and_lowercased(self):
        body = RegisterRequest(email="Khan.Test@Gmail.com ", name="Khan", password="secret1")
        assert body.email == "khan.test@gmail.com"

    def test_password_is_not_altered(self):
        assert LoginRequest(email="a@b.co", password=" PaSs ").password == " PaSs "


requires_postgres = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs PostgreSQL via DATABASE_URL"
)


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = build_engine(load_settings().database_url, pool_size=1, max_overflow=0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield build_session_factory(engine)
    await engine.dispose()


@requires_postgres
class TestPostgresUserStoreMatching:
    async def test_mixed_case_stored_email_still_logs_in(self, factory):
        tag = uuid.uuid4().hex[:8]
        stored = f"Mixed.Case-{tag}@Example.com"
        user_id = str(uuid.uuid4())
        async with factory() as session, session.begin():
            session.add(
                UserRow(id=user_id, email=stored, name="M", password_hash=hash_password("pw123456"))
            )
        store = PostgresUserStore(factory)
        try:
            user = await store.authenticate(f"  mixed.case-{tag}@example.COM ", "pw123456")
            assert user is not None and user.id == user_id
            assert await store.authenticate(stored, "wrong-password") is None
            assert await store.email_exists(stored.lower()) is True
        finally:
            async with factory() as session, session.begin():
                await session.execute(delete(UserRow).where(UserRow.id == user_id))

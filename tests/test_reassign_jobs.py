"""Tests for the reassign_jobs operational script.

The database tests need a real PostgreSQL (the models use JSONB); they run in
CI's integration job, which provides one via DATABASE_URL, and skip elsewhere.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from researchforge.config import load_settings
from researchforge.database.engine import build_engine, build_session_factory
from researchforge.database.models import Base, ResearchJobRow, UserRow
from researchforge.scripts import reassign_jobs as script


class TestCli:
    def test_defaults_to_dry_run_and_anonymous_owners(self):
        args = script._parse_args(["--email", "a@example.com"])
        assert args.apply is False
        assert args.from_owners is None

    def test_repeatable_from_user(self):
        args = script._parse_args(
            ["--email", "a@example.com", "--from-user", "x", "--from-user", "y"]
        )
        assert args.from_owners == ["x", "y"]

    async def test_missing_database_url_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert await script._main(["--email", "a@example.com"]) == 2
        assert "DATABASE_URL" in capsys.readouterr().err


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


@pytest.fixture
async def seeded(factory):
    """Create a user plus anonymous, other-user and already-owned jobs; clean up after."""
    tag = uuid.uuid4().hex[:8]
    user = UserRow(id=str(uuid.uuid4()), email=f"Owner-{tag}@Example.com", name="Owner")
    other_owner = f"other-{tag}"
    jobs = {
        "anon": ResearchJobRow(id=str(uuid.uuid4()), user_id="anonymous", question=f"anon {tag}"),
        "blank": ResearchJobRow(id=str(uuid.uuid4()), user_id="", question=f"blank {tag}"),
        "other": ResearchJobRow(id=str(uuid.uuid4()), user_id=other_owner, question=f"o {tag}"),
        "mine": ResearchJobRow(id=str(uuid.uuid4()), user_id=user.id, question=f"mine {tag}"),
    }
    for job in jobs.values():
        job.status = "completed"
        job.created_at = datetime.now(UTC)
    async with factory() as session, session.begin():
        session.add(user)
        session.add_all(jobs.values())
    yield user, jobs, other_owner
    async with factory() as session, session.begin():
        await session.execute(
            delete(ResearchJobRow).where(ResearchJobRow.id.in_([j.id for j in jobs.values()]))
        )
        await session.execute(delete(UserRow).where(UserRow.id == user.id))


async def _owners(factory, jobs) -> dict[str, str]:
    async with factory() as session:
        rows = await session.execute(
            select(ResearchJobRow.id, ResearchJobRow.user_id).where(
                ResearchJobRow.id.in_([j.id for j in jobs.values()])
            )
        )
        by_id = {r.id: r.user_id for r in rows}
    return {name: by_id[job.id] for name, job in jobs.items()}


@requires_postgres
class TestReassignAgainstPostgres:
    async def test_dry_run_changes_nothing(self, factory, seeded):
        user, jobs, _ = seeded
        before = await _owners(factory, jobs)

        target, preview = await script.reassign_jobs(factory, email=user.email)

        assert target == user.id
        assert {jobs["anon"].id, jobs["blank"].id} <= {p.id for p in preview}
        assert await _owners(factory, jobs) == before

    async def test_apply_moves_only_anonymous_jobs(self, factory, seeded):
        user, jobs, other_owner = seeded

        await script.reassign_jobs(factory, email=user.email.lower(), apply=True)

        owners = await _owners(factory, jobs)
        assert owners["anon"] == user.id
        assert owners["blank"] == user.id
        assert owners["other"] == other_owner
        assert owners["mine"] == user.id

    async def test_from_user_limits_the_source(self, factory, seeded):
        user, jobs, other_owner = seeded

        _, preview = await script.reassign_jobs(
            factory, email=user.email, from_owners=(other_owner,), apply=True
        )

        assert [p.id for p in preview] == [jobs["other"].id]
        owners = await _owners(factory, jobs)
        assert owners["other"] == user.id
        assert owners["anon"] == "anonymous"

    async def test_unknown_email_is_an_error(self, factory, seeded):
        with pytest.raises(script.ReassignError, match="No user registered"):
            await script.reassign_jobs(factory, email="nobody@example.com", apply=True)

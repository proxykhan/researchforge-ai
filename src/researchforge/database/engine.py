"""Async SQLAlchemy engine and session factory.

Usage in app startup::

    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        ...  # Alembic handles schema creation in production

    # In request handlers, get a session via get_session(engine).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async engine from a database URL.

    The URL must use the ``postgresql+asyncpg://`` scheme.
    ``echo=True`` logs every SQL statement — useful during development.
    """
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session that auto-commits on success and rolls back on error."""
    async with factory() as session:
        yield session

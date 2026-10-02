"""Give research jobs created while auth was disabled to a real account.

With ``AUTH_ENABLED`` off, every job is saved under the ``anonymous`` user, so
once auth is turned on those jobs belong to nobody and vanish from history.

Dry run (default) lists what would change; nothing is written::

    python -m researchforge.scripts.reassign_jobs --email you@example.com

Apply the change in a single transaction::

    python -m researchforge.scripts.reassign_jobs --email you@example.com --apply

The database is read from ``DATABASE_URL`` (the same variable the API uses).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from researchforge.config import load_settings
from researchforge.database.engine import build_engine, build_session_factory
from researchforge.database.models import ResearchJobRow, UserRow

DEFAULT_SOURCE_OWNERS = ("anonymous", "")


class ReassignError(Exception):
    """A problem the operator must fix before the script can run."""


@dataclass(frozen=True)
class JobPreview:
    id: str
    user_id: str
    question: str
    created_at: str


async def resolve_user_id(session: AsyncSession, email: str) -> str:
    """Look up the target account by email (case-insensitive)."""
    result = await session.execute(
        select(UserRow.id, UserRow.is_active).where(
            func.lower(UserRow.email) == email.strip().lower()
        )
    )
    row = result.first()
    if row is None:
        raise ReassignError(f"No user registered with email {email!r}. Sign up first.")
    if not row.is_active:
        raise ReassignError(f"User {email!r} is deactivated.")
    return str(row.id)


async def reassign_jobs(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    from_owners: Sequence[str] = DEFAULT_SOURCE_OWNERS,
    apply: bool = False,
) -> tuple[str, list[JobPreview]]:
    """Return the target user id and the matching jobs; update them when ``apply``.

    The lookup and update happen in one transaction, so jobs created concurrently
    are either all moved or not touched.
    """
    # Closing the session without commit() rolls back, which is what a dry run wants.
    async with session_factory() as session:
        target_id = await resolve_user_id(session, email)
        if target_id in from_owners:
            raise ReassignError("Target user is one of the source owners; nothing to do.")

        rows = await session.execute(
            select(
                ResearchJobRow.id,
                ResearchJobRow.user_id,
                ResearchJobRow.question,
                ResearchJobRow.created_at,
            )
            .where(ResearchJobRow.user_id.in_(list(from_owners)))
            .order_by(ResearchJobRow.created_at)
            .with_for_update()
        )
        jobs = [
            JobPreview(
                id=r.id, user_id=r.user_id, question=r.question, created_at=str(r.created_at)
            )
            for r in rows
        ]

        if apply and jobs:
            await session.execute(
                update(ResearchJobRow)
                .where(ResearchJobRow.id.in_([j.id for j in jobs]))
                .values(user_id=target_id)
            )
            await session.commit()

    return target_id, jobs


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m researchforge.scripts.reassign_jobs",
        description="Reassign research jobs created while auth was disabled to a real account.",
    )
    parser.add_argument("--email", required=True, help="email of the account that should own them")
    parser.add_argument(
        "--from-user",
        action="append",
        dest="from_owners",
        metavar="USER_ID",
        help="owner id to move jobs from (repeatable; default: 'anonymous' and empty)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="write the change (default is a dry run)"
    )
    return parser.parse_args(argv)


async def _main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = load_settings().database_url
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2

    engine = build_engine(database_url, pool_size=1, max_overflow=0)
    try:
        target_id, jobs = await reassign_jobs(
            build_session_factory(engine),
            email=args.email,
            from_owners=tuple(args.from_owners or DEFAULT_SOURCE_OWNERS),
            apply=args.apply,
        )
    except ReassignError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    verb = "Reassigned" if args.apply else "Would reassign"
    print(f"{verb} {len(jobs)} job(s) to {args.email} (user id {target_id}):")
    for job in jobs:
        print(f"  {job.created_at[:19]}  {job.id}  {job.question[:70]}")
    if not args.apply and jobs:
        print("\nDry run only. Re-run with --apply to make the change.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

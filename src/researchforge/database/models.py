"""SQLAlchemy ORM models.

Uses the SQLAlchemy 2.0 Mapped[] annotation style for full type-checker support.
Only entities that the codebase actively uses are defined here — additional
tables (documents, chunks, claims, citations, …) will be added in the phases
that introduce the features that need them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared base for all ORM models."""


class UserRow(Base):
    """A registered API user.

    Authentication is API-key-based: the client sends a key in the
    Authorization header, we store only its SHA-256 hash.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ResearchJobRow(Base):
    """Persistent representation of a research job.

    Replaces the in-memory ResearchJob dataclass for production use.
    JSON columns store variable-length data (search queries, paper metadata,
    evaluation scores) without requiring separate join tables at this stage.
    """

    __tablename__ = "research_jobs"
    __table_args__ = (
        Index("ix_research_jobs_user_id", "user_id"),
        Index("ix_research_jobs_status", "status"),
        Index("ix_research_jobs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    search_queries: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    papers: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    synthesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

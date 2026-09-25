"""Data models for the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata attached to each document chunk for filtering and traceability."""

    document_id: str
    paper_id: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    source: str | None = None
    url: str | None = None
    doi: str | None = None
    published_date: str | None = None
    section: str | None = None
    chunk_index: int = 0
    ingested_at: datetime | None = None


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of text with its embedding and metadata.

    This is the unit of storage and retrieval in the RAG pipeline.
    """

    chunk_id: str
    text: str
    metadata: ChunkMetadata
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalResult:
    """A chunk returned by the retriever, scored for relevance."""

    chunk: DocumentChunk
    score: float
    method: str

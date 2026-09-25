"""Vector store abstraction and in-memory implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from researchforge.rag.embeddings import cosine_similarity
from researchforge.rag.models import DocumentChunk, RetrievalResult


class VectorStore(ABC):
    """Interface for vector storage backends.

    Replaced by a pgvector-backed implementation in Phase 9.
    """

    @abstractmethod
    async def add(self, chunks: list[DocumentChunk]) -> None:
        """Store chunks with their embeddings."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Find the most similar chunks to the query embedding."""

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Find chunks matching keywords in the query."""

    @abstractmethod
    async def count(self) -> int:
        """Return the number of stored chunks."""


@dataclass
class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store using brute-force cosine similarity."""

    _chunks: list[DocumentChunk] = field(default_factory=list)

    async def add(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        candidates = self._filter(source_filter)
        scored: list[RetrievalResult] = []

        for chunk in candidates:
            if not chunk.embedding:
                continue
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored.append(RetrievalResult(chunk=chunk, score=score, method="semantic"))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        candidates = self._filter(source_filter)
        keywords = set(query.lower().split())

        scored: list[RetrievalResult] = []
        for chunk in candidates:
            text_lower = chunk.text.lower()
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                score = matches / len(keywords) if keywords else 0.0
                scored.append(RetrievalResult(chunk=chunk, score=score, method="keyword"))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    async def count(self) -> int:
        return len(self._chunks)

    def _filter(self, source_filter: str | None) -> list[DocumentChunk]:
        if source_filter is None:
            return self._chunks
        return [c for c in self._chunks if c.metadata.source == source_filter]

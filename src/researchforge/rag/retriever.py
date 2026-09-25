"""Retriever — semantic, keyword, and hybrid search over the vector store."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from researchforge.rag.embeddings import EmbeddingProvider
from researchforge.rag.models import RetrievalResult
from researchforge.rag.store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class Retriever:
    """Runs semantic, keyword, or hybrid retrieval against the vector store."""

    store: VectorStore
    embeddings: EmbeddingProvider
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Pure semantic (embedding) search."""
        vectors = await self.embeddings.embed([query])
        return await self.store.search(vectors[0], top_k=top_k, source_filter=source_filter)

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Pure keyword search."""
        return await self.store.keyword_search(query, top_k=top_k, source_filter=source_filter)

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Combine semantic and keyword search using reciprocal rank fusion."""
        semantic_results = await self.semantic_search(
            query, top_k=top_k * 2, source_filter=source_filter
        )
        keyword_results = await self.keyword_search(
            query, top_k=top_k * 2, source_filter=source_filter
        )

        fused = _reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            weight_a=self.semantic_weight,
            weight_b=self.keyword_weight,
        )

        logger.info(
            "Hybrid search: %d semantic + %d keyword → %d fused results",
            len(semantic_results),
            len(keyword_results),
            len(fused),
        )
        return fused[:top_k]


def _reciprocal_rank_fusion(
    results_a: list[RetrievalResult],
    results_b: list[RetrievalResult],
    weight_a: float = 0.7,
    weight_b: float = 0.3,
    k: int = 60,
) -> list[RetrievalResult]:
    """Merge two ranked lists using weighted reciprocal rank fusion.

    RRF score = weight * (1 / (k + rank)).  Higher is better.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievalResult] = {}

    for rank, result in enumerate(results_a):
        cid = result.chunk.chunk_id
        scores[cid] = scores.get(cid, 0) + weight_a / (k + rank + 1)
        chunk_map[cid] = result

    for rank, result in enumerate(results_b):
        cid = result.chunk.chunk_id
        scores[cid] = scores.get(cid, 0) + weight_b / (k + rank + 1)
        if cid not in chunk_map:
            chunk_map[cid] = result

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [
        RetrievalResult(
            chunk=chunk_map[cid].chunk,
            score=scores[cid],
            method="hybrid",
        )
        for cid in ranked_ids
    ]

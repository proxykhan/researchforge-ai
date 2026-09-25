"""Ingestion pipeline — processes papers into embedded chunks in the vector store."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from researchforge.integrations.models import PaperResult
from researchforge.rag.chunker import TextChunker
from researchforge.rag.embeddings import EmbeddingProvider
from researchforge.rag.models import DocumentChunk
from researchforge.rag.store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionPipeline:
    """Ingests papers: chunk → embed → store."""

    store: VectorStore
    embeddings: EmbeddingProvider
    chunker: TextChunker = field(default_factory=TextChunker)

    async def ingest_papers(self, papers: list[PaperResult]) -> int:
        """Process papers into embedded chunks. Returns the number of chunks stored."""
        all_chunks: list[DocumentChunk] = []
        for paper in papers:
            chunks = self.chunker.chunk_paper(paper)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        texts = [c.text for c in all_chunks]
        embeddings = await self.embeddings.embed(texts)

        embedded_chunks = [
            DocumentChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                metadata=chunk.metadata,
                embedding=emb,
            )
            for chunk, emb in zip(all_chunks, embeddings, strict=True)
        ]

        await self.store.add(embedded_chunks)
        logger.info("Ingested %d papers into %d chunks", len(papers), len(embedded_chunks))
        return len(embedded_chunks)

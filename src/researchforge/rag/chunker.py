"""Text chunker — splits text into overlapping chunks."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from researchforge.integrations.models import PaperResult
from researchforge.rag.models import ChunkMetadata, DocumentChunk

_SECTION_PATTERN = re.compile(
    r"^(?:#{1,3}\s+.+|[A-Z][A-Z\s]{2,}:?\s*$|(?:\d+\.)+\s+.+)",
    re.MULTILINE,
)


@dataclass
class TextChunker:
    """Splits text into overlapping chunks preserving paragraph boundaries.

    chunk_size: target characters per chunk (soft limit — won't split mid-paragraph).
    chunk_overlap: characters of overlap between consecutive chunks.
    """

    chunk_size: int = 800
    chunk_overlap: int = 200

    def chunk_text(
        self,
        text: str,
        metadata: ChunkMetadata,
    ) -> list[DocumentChunk]:
        """Split text into chunks, each tagged with metadata."""
        if not text or not text.strip():
            return []

        paragraphs = _split_paragraphs(text)
        chunks: list[DocumentChunk] = []
        current_parts: list[str] = []
        current_len = 0
        section: str | None = metadata.section

        for para in paragraphs:
            section_match = _SECTION_PATTERN.match(para)
            if section_match:
                section = para.strip().rstrip(":")

            if current_len + len(para) > self.chunk_size and current_parts:
                chunk_text = "\n\n".join(current_parts)
                chunk_meta = ChunkMetadata(
                    document_id=metadata.document_id,
                    paper_id=metadata.paper_id,
                    title=metadata.title,
                    authors=metadata.authors,
                    source=metadata.source,
                    url=metadata.url,
                    doi=metadata.doi,
                    published_date=metadata.published_date,
                    section=section,
                    chunk_index=len(chunks),
                    ingested_at=metadata.ingested_at,
                )
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=chunk_text,
                        metadata=chunk_meta,
                    )
                )
                overlap_parts = _get_overlap_parts(current_parts, self.chunk_overlap)
                current_parts = overlap_parts
                current_len = sum(len(p) for p in current_parts)

            current_parts.append(para)
            current_len += len(para)

        if current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunk_meta = ChunkMetadata(
                document_id=metadata.document_id,
                paper_id=metadata.paper_id,
                title=metadata.title,
                authors=metadata.authors,
                source=metadata.source,
                url=metadata.url,
                doi=metadata.doi,
                published_date=metadata.published_date,
                section=section,
                chunk_index=len(chunks),
                ingested_at=metadata.ingested_at,
            )
            chunks.append(
                DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    metadata=chunk_meta,
                )
            )

        return chunks

    def chunk_paper(self, paper: PaperResult) -> list[DocumentChunk]:
        """Convenience: chunk a PaperResult's abstract."""
        if not paper.abstract:
            return []

        metadata = ChunkMetadata(
            document_id=f"{paper.source}:{paper.source_id}",
            paper_id=paper.source_id,
            title=paper.title,
            authors=[a.name for a in paper.authors],
            source=paper.source,
            url=paper.url,
            doi=paper.doi,
            published_date=str(paper.published_date) if paper.published_date else None,
            section="abstract",
            ingested_at=datetime.now(UTC),
        )
        return self.chunk_text(paper.abstract, metadata)


def _split_paragraphs(text: str) -> list[str]:
    """Split text on double-newlines, keeping non-empty paragraphs."""
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _get_overlap_parts(parts: list[str], overlap_chars: int) -> list[str]:
    """Return trailing paragraphs whose combined length is ≤ overlap_chars."""
    result: list[str] = []
    total = 0
    for part in reversed(parts):
        if total + len(part) > overlap_chars and result:
            break
        result.append(part)
        total += len(part)
    result.reverse()
    return result

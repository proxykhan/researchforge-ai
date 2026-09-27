"""Tests for the RAG pipeline (Phase 5)."""

from __future__ import annotations

from researchforge.integrations.models import Author, PaperResult
from researchforge.rag.chunker import TextChunker, _get_overlap_parts, _split_paragraphs
from researchforge.rag.embeddings import (
    HashEmbeddingProvider,
    _tokenize,
    cosine_similarity,
)
from researchforge.rag.ingest import IngestionPipeline
from researchforge.rag.models import ChunkMetadata, DocumentChunk, RetrievalResult
from researchforge.rag.retriever import Retriever, _reciprocal_rank_fusion
from researchforge.rag.store import InMemoryVectorStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PAPER = PaperResult(
    source="arxiv",
    source_id="2301.00001",
    title="Attention Is All You Need",
    authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer")],
    abstract=(
        "The dominant sequence transduction models are based on complex recurrent or "
        "convolutional neural networks that include an encoder and a decoder. The best "
        "performing models also connect the encoder and decoder through an attention "
        "mechanism. We propose a new simple network architecture, the Transformer, "
        "based solely on attention mechanisms, dispensing with recurrence and convolutions "
        "entirely. Experiments on two machine translation tasks show these models to be "
        "superior in quality while being more parallelizable and requiring significantly "
        "less time to train."
    ),
    url="https://arxiv.org/abs/1706.03762",
    doi="10.48550/arXiv.1706.03762",
    citation_count=90000,
)


def _make_metadata(**kwargs: object) -> ChunkMetadata:
    defaults: dict[str, object] = {
        "document_id": "test-doc-1",
        "paper_id": "123",
        "title": "Test Paper",
        "source": "test",
    }
    defaults.update(kwargs)
    return ChunkMetadata(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_chunk_metadata_defaults(self) -> None:
        meta = ChunkMetadata(document_id="doc-1")
        assert meta.document_id == "doc-1"
        assert meta.chunk_index == 0
        assert meta.authors == []

    def test_document_chunk_creation(self) -> None:
        meta = _make_metadata()
        chunk = DocumentChunk(chunk_id="c1", text="Hello world", metadata=meta)
        assert chunk.text == "Hello world"
        assert chunk.embedding == []

    def test_retrieval_result(self) -> None:
        meta = _make_metadata()
        chunk = DocumentChunk(chunk_id="c1", text="test", metadata=meta)
        result = RetrievalResult(chunk=chunk, score=0.95, method="semantic")
        assert result.score == 0.95
        assert result.method == "semantic"


# ---------------------------------------------------------------------------
# Chunker tests
# ---------------------------------------------------------------------------


class TestSplitParagraphs:
    def test_splits_on_double_newline(self) -> None:
        text = "First paragraph.\n\nSecond paragraph."
        assert _split_paragraphs(text) == ["First paragraph.", "Second paragraph."]

    def test_strips_whitespace(self) -> None:
        text = "  First.  \n\n  Second.  "
        assert _split_paragraphs(text) == ["First.", "Second."]

    def test_empty_text(self) -> None:
        assert _split_paragraphs("") == []
        assert _split_paragraphs("   ") == []

    def test_single_paragraph(self) -> None:
        assert _split_paragraphs("One paragraph.") == ["One paragraph."]


class TestGetOverlapParts:
    def test_returns_trailing_parts_within_limit(self) -> None:
        parts = ["first paragraph that is long enough", "medium text", "last part"]
        result = _get_overlap_parts(parts, overlap_chars=25)
        assert result == ["medium text", "last part"]

    def test_returns_all_if_within_limit(self) -> None:
        parts = ["a", "b", "c"]
        result = _get_overlap_parts(parts, overlap_chars=100)
        assert result == ["a", "b", "c"]

    def test_returns_last_if_first_exceeds(self) -> None:
        parts = ["very long text that is too big", "small"]
        result = _get_overlap_parts(parts, overlap_chars=10)
        assert result == ["small"]


class TestTextChunker:
    def test_chunks_short_text(self) -> None:
        chunker = TextChunker(chunk_size=500)
        meta = _make_metadata()
        chunks = chunker.chunk_text("A short paragraph.", meta)
        assert len(chunks) == 1
        assert chunks[0].text == "A short paragraph."

    def test_chunks_long_text(self) -> None:
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "\n\n".join(f"Paragraph {i} with some filler text." for i in range(10))
        meta = _make_metadata()
        chunks = chunker.chunk_text(text, meta)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.metadata.document_id == "test-doc-1"

    def test_chunk_indices_increment(self) -> None:
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "\n\n".join(f"Paragraph {i} is here." for i in range(5))
        meta = _make_metadata()
        chunks = chunker.chunk_text(text, meta)
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_text_returns_empty(self) -> None:
        chunker = TextChunker()
        meta = _make_metadata()
        assert chunker.chunk_text("", meta) == []
        assert chunker.chunk_text("   ", meta) == []

    def test_chunk_paper(self) -> None:
        chunker = TextChunker(chunk_size=200)
        chunks = chunker.chunk_paper(SAMPLE_PAPER)
        assert len(chunks) >= 1
        assert chunks[0].metadata.paper_id == "2301.00001"
        assert chunks[0].metadata.source == "arxiv"
        assert chunks[0].metadata.title == "Attention Is All You Need"
        assert chunks[0].metadata.section == "abstract"

    def test_chunk_paper_no_abstract(self) -> None:
        paper = PaperResult(
            source="test",
            source_id="1",
            title="No Abstract",
            authors=[],
            abstract="",
            url="",
        )
        chunker = TextChunker()
        assert chunker.chunk_paper(paper) == []


# ---------------------------------------------------------------------------
# Embedding tests
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_basic_tokenization(self) -> None:
        tokens = _tokenize("Deep learning for NLP tasks")
        assert "deep" in tokens
        assert "learning" in tokens
        assert "nlp" in tokens

    def test_removes_stop_words(self) -> None:
        tokens = _tokenize("the quick and the slow")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "slow" in tokens

    def test_empty_input(self) -> None:
        assert _tokenize("") == []


class TestHashEmbeddingProvider:
    async def test_produces_correct_dimensions(self) -> None:
        provider = HashEmbeddingProvider(_dimensions=128)
        vectors = await provider.embed(["Hello world"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 128

    async def test_batch_embedding(self) -> None:
        provider = HashEmbeddingProvider()
        vectors = await provider.embed(["text one", "text two", "text three"])
        assert len(vectors) == 3

    async def test_similar_texts_have_high_similarity(self) -> None:
        provider = HashEmbeddingProvider()
        vecs = await provider.embed(
            [
                "deep learning neural networks",
                "neural network deep learning models",
                "cooking recipes for pasta",
            ]
        )
        sim_related = cosine_similarity(vecs[0], vecs[1])
        sim_unrelated = cosine_similarity(vecs[0], vecs[2])
        assert sim_related > sim_unrelated

    async def test_empty_text_returns_zero_vector(self) -> None:
        provider = HashEmbeddingProvider(_dimensions=64)
        vecs = await provider.embed([""])
        assert all(v == 0.0 for v in vecs[0])

    async def test_name_and_dimensions(self) -> None:
        provider = HashEmbeddingProvider(_dimensions=512)
        assert provider.name == "hash"
        assert provider.dimensions == 512


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0

    def test_orthogonal_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


# ---------------------------------------------------------------------------
# Vector store tests
# ---------------------------------------------------------------------------


class TestInMemoryVectorStore:
    async def test_add_and_count(self) -> None:
        store = InMemoryVectorStore()
        meta = _make_metadata()
        chunks = [
            DocumentChunk(chunk_id="c1", text="hello", metadata=meta, embedding=[1.0, 0.0]),
            DocumentChunk(chunk_id="c2", text="world", metadata=meta, embedding=[0.0, 1.0]),
        ]
        await store.add(chunks)
        assert await store.count() == 2

    async def test_semantic_search(self) -> None:
        store = InMemoryVectorStore()
        meta = _make_metadata()
        chunks = [
            DocumentChunk(chunk_id="c1", text="hello", metadata=meta, embedding=[1.0, 0.0]),
            DocumentChunk(chunk_id="c2", text="world", metadata=meta, embedding=[0.0, 1.0]),
        ]
        await store.add(chunks)

        results = await store.search([1.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "c1"
        assert results[0].method == "semantic"

    async def test_keyword_search(self) -> None:
        store = InMemoryVectorStore()
        meta = _make_metadata()
        chunks = [
            DocumentChunk(chunk_id="c1", text="Deep learning for NLP", metadata=meta),
            DocumentChunk(chunk_id="c2", text="Cooking pasta recipes", metadata=meta),
        ]
        await store.add(chunks)

        results = await store.keyword_search("deep learning", top_k=5)
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "c1"
        assert results[0].method == "keyword"

    async def test_source_filter(self) -> None:
        store = InMemoryVectorStore()
        meta_arxiv = _make_metadata(source="arxiv")
        meta_scholar = _make_metadata(source="scholar")
        chunks = [
            DocumentChunk(
                chunk_id="c1", text="arxiv paper", metadata=meta_arxiv, embedding=[1.0, 0.0]
            ),
            DocumentChunk(
                chunk_id="c2", text="scholar paper", metadata=meta_scholar, embedding=[0.9, 0.1]
            ),
        ]
        await store.add(chunks)

        results = await store.search([1.0, 0.0], source_filter="arxiv")
        assert len(results) == 1
        assert results[0].chunk.metadata.source == "arxiv"

    async def test_empty_store(self) -> None:
        store = InMemoryVectorStore()
        results = await store.search([1.0, 0.0])
        assert results == []
        assert await store.count() == 0


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------


class TestRetriever:
    async def _make_retriever(self) -> Retriever:
        embeddings = HashEmbeddingProvider(_dimensions=64)
        store = InMemoryVectorStore()

        meta = _make_metadata()

        texts = [
            "Transformer models use self-attention mechanisms for sequence processing.",
            "Recurrent neural networks process sequences step by step.",
            "Convolutional networks are commonly used for image classification.",
        ]
        all_chunks: list[DocumentChunk] = []
        for i, text in enumerate(texts):
            m = ChunkMetadata(
                document_id=meta.document_id,
                paper_id=meta.paper_id,
                title=meta.title,
                source=meta.source,
                chunk_index=i,
            )
            vec = (await embeddings.embed([text]))[0]
            all_chunks.append(DocumentChunk(chunk_id=f"c{i}", text=text, metadata=m, embedding=vec))

        await store.add(all_chunks)
        return Retriever(store=store, embeddings=embeddings)

    async def test_semantic_search(self) -> None:
        retriever = await self._make_retriever()
        results = await retriever.semantic_search("attention transformer", top_k=2)
        assert len(results) <= 2
        ids = {r.chunk.chunk_id for r in results}
        assert "c0" in ids

    async def test_keyword_search(self) -> None:
        retriever = await self._make_retriever()
        results = await retriever.keyword_search("convolutional image", top_k=2)
        assert len(results) >= 1
        assert any(r.chunk.chunk_id == "c2" for r in results)

    async def test_hybrid_search(self) -> None:
        retriever = await self._make_retriever()
        results = await retriever.hybrid_search("transformer attention", top_k=3)
        assert len(results) >= 1
        assert results[0].method == "hybrid"

    async def test_hybrid_deduplicates(self) -> None:
        retriever = await self._make_retriever()
        results = await retriever.hybrid_search("transformer attention", top_k=10)
        chunk_ids = [r.chunk.chunk_id for r in results]
        assert len(chunk_ids) == len(set(chunk_ids))


class TestReciprocalRankFusion:
    def test_merges_two_lists(self) -> None:
        meta = _make_metadata()
        c1 = DocumentChunk(chunk_id="c1", text="a", metadata=meta)
        c2 = DocumentChunk(chunk_id="c2", text="b", metadata=meta)
        c3 = DocumentChunk(chunk_id="c3", text="c", metadata=meta)

        list_a = [
            RetrievalResult(chunk=c1, score=0.9, method="semantic"),
            RetrievalResult(chunk=c2, score=0.7, method="semantic"),
        ]
        list_b = [
            RetrievalResult(chunk=c2, score=0.8, method="keyword"),
            RetrievalResult(chunk=c3, score=0.6, method="keyword"),
        ]

        fused = _reciprocal_rank_fusion(list_a, list_b)
        assert len(fused) == 3
        assert all(r.method == "hybrid" for r in fused)
        chunk_ids = [r.chunk.chunk_id for r in fused]
        assert "c2" in chunk_ids

    def test_empty_lists(self) -> None:
        assert _reciprocal_rank_fusion([], []) == []


# ---------------------------------------------------------------------------
# Ingestion pipeline tests
# ---------------------------------------------------------------------------


class TestIngestionPipeline:
    async def test_ingest_papers(self) -> None:
        store = InMemoryVectorStore()
        embeddings = HashEmbeddingProvider(_dimensions=64)
        pipeline = IngestionPipeline(store=store, embeddings=embeddings)

        count = await pipeline.ingest_papers([SAMPLE_PAPER])
        assert count >= 1
        assert await store.count() == count

    async def test_ingest_empty_papers(self) -> None:
        store = InMemoryVectorStore()
        embeddings = HashEmbeddingProvider()
        pipeline = IngestionPipeline(store=store, embeddings=embeddings)

        count = await pipeline.ingest_papers([])
        assert count == 0
        assert await store.count() == 0

    async def test_ingest_paper_without_abstract(self) -> None:
        paper = PaperResult(
            source="test",
            source_id="1",
            title="Empty",
            authors=[],
            abstract="",
            url="",
        )
        store = InMemoryVectorStore()
        embeddings = HashEmbeddingProvider()
        pipeline = IngestionPipeline(store=store, embeddings=embeddings)

        count = await pipeline.ingest_papers([paper])
        assert count == 0

    async def test_ingested_chunks_are_retrievable(self) -> None:
        store = InMemoryVectorStore()
        embeddings = HashEmbeddingProvider(_dimensions=64)
        pipeline = IngestionPipeline(store=store, embeddings=embeddings)

        await pipeline.ingest_papers([SAMPLE_PAPER])

        retriever = Retriever(store=store, embeddings=embeddings)
        results = await retriever.semantic_search("attention transformer", top_k=5)
        assert len(results) >= 1
        assert results[0].chunk.metadata.title == "Attention Is All You Need"

"""Tests for research integration data models."""

from datetime import date

from researchforge.integrations.models import (
    Author,
    PaperResult,
    SearchQuery,
    SearchResponse,
)


class TestAuthor:
    def test_create_author(self):
        author = Author(name="Jane Doe", affiliation="MIT")
        assert author.name == "Jane Doe"
        assert author.affiliation == "MIT"

    def test_author_without_affiliation(self):
        author = Author(name="John Smith")
        assert author.affiliation is None


class TestPaperResult:
    def _make_paper(self, **overrides: object) -> PaperResult:
        return PaperResult(
            source=str(overrides.get("source", "arxiv")),
            source_id=str(overrides.get("source_id", "2401.00001")),
            title=str(overrides.get("title", "Test Paper")),
            authors=overrides.get("authors", [Author(name="Alice"), Author(name="Bob")]),  # type: ignore[arg-type]
            abstract=str(overrides.get("abstract", "A test abstract.")),
            url=str(overrides.get("url", "https://arxiv.org/abs/2401.00001")),
            published_date=overrides.get("published_date"),  # type: ignore[arg-type]
            doi=overrides.get("doi"),  # type: ignore[arg-type]
            pdf_url=overrides.get("pdf_url"),  # type: ignore[arg-type]
            categories=overrides.get("categories", []),  # type: ignore[arg-type]
            citation_count=overrides.get("citation_count"),  # type: ignore[arg-type]
        )

    def test_display_authors_two(self):
        paper = self._make_paper()
        assert paper.display_authors == "Alice, Bob"

    def test_display_authors_truncated(self):
        authors = [Author(name=n) for n in ["A", "B", "C", "D"]]
        paper = self._make_paper(authors=authors)
        assert paper.display_authors == "A, B, C et al."

    def test_display_authors_empty(self):
        paper = self._make_paper(authors=[])
        assert paper.display_authors == "Unknown"

    def test_optional_fields_default(self):
        paper = self._make_paper()
        assert paper.published_date is None
        assert paper.doi is None
        assert paper.pdf_url is None
        assert paper.categories == []
        assert paper.citation_count is None

    def test_optional_fields_set(self):
        paper = self._make_paper(
            published_date=date(2024, 1, 15),
            doi="10.1234/test",
            pdf_url="https://arxiv.org/pdf/2401.00001",
            categories=["cs.AI"],
            citation_count=42,
        )
        assert paper.published_date == date(2024, 1, 15)
        assert paper.doi == "10.1234/test"
        assert paper.citation_count == 42


class TestSearchQuery:
    def test_defaults(self):
        q = SearchQuery(query="transformers")
        assert q.query == "transformers"
        assert q.max_results == 10
        assert q.sort_by == "relevance"
        assert q.year_from is None

    def test_custom(self):
        q = SearchQuery(query="rag", max_results=20, year_from=2023)
        assert q.max_results == 20
        assert q.year_from == 2023


class TestSearchResponse:
    def test_empty_response(self):
        resp = SearchResponse(provider="test", query="q", total_results=0, papers=[])
        assert resp.papers == []
        assert resp.total_results == 0

"""Tests for the SemanticScholarProvider."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from researchforge.integrations.models import SearchQuery
from researchforge.integrations.semantic_scholar import (
    SemanticScholarProvider,
    _parse_paper,
)

SAMPLE_S2_RESPONSE = {
    "total": 1,
    "data": [
        {
            "paperId": "abc123",
            "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "abstract": "Large pre-trained language models store factual knowledge.",
            "authors": [
                {"authorId": "1", "name": "Patrick Lewis"},
                {"authorId": "2", "name": "Ethan Perez"},
            ],
            "year": 2020,
            "publicationDate": "2020-05-22",
            "externalIds": {"DOI": "10.5555/test", "ArXiv": "2005.11401"},
            "url": "https://www.semanticscholar.org/paper/abc123",
            "citationCount": 3500,
            "fieldsOfStudy": ["Computer Science"],
            "isOpenAccess": True,
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2005.11401"},
        }
    ],
}


def _mock_json_response(data: dict, status_code: int = 200) -> httpx.Response:
    import json

    return httpx.Response(
        status_code=status_code,
        text=json.dumps(data),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://test"),
    )


class TestParsePaper:
    def test_parse_full_paper(self):
        paper = _parse_paper(SAMPLE_S2_RESPONSE["data"][0])
        assert paper is not None
        assert paper.source == "semantic_scholar"
        assert paper.source_id == "abc123"
        assert paper.title == "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Patrick Lewis"
        assert paper.published_date == date(2020, 5, 22)
        assert paper.doi == "10.5555/test"
        assert paper.pdf_url == "https://arxiv.org/pdf/2005.11401"
        assert paper.citation_count == 3500
        assert paper.categories == ["Computer Science"]

    def test_parse_missing_title_returns_none(self):
        assert _parse_paper({"paperId": "x"}) is None
        assert _parse_paper({"paperId": "x", "title": ""}) is None

    def test_parse_minimal_paper(self):
        paper = _parse_paper({"paperId": "min1", "title": "Minimal Paper"})
        assert paper is not None
        assert paper.title == "Minimal Paper"
        assert paper.authors == []
        assert paper.published_date is None
        assert paper.doi is None


class TestSemanticScholarProvider:
    @pytest.fixture
    def provider(self):
        return SemanticScholarProvider(api_key="test-key", timeout=5.0, max_retries=1)

    async def test_name(self, provider):
        assert provider.name == "semantic_scholar"

    async def test_search_returns_papers(self, provider):
        mock_resp = _mock_json_response(SAMPLE_S2_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="RAG"))

        assert result.provider == "semantic_scholar"
        assert result.total_results == 1
        assert len(result.papers) == 1
        assert result.papers[0].source_id == "abc123"

    async def test_search_empty(self, provider):
        mock_resp = _mock_json_response({"total": 0, "data": []})

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="nonexistent"))

        assert result.total_results == 0
        assert result.papers == []

    async def test_search_with_year_filter(self, provider):
        mock_resp = _mock_json_response({"total": 0, "data": []})

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ) as mock:
            await provider.search(SearchQuery(query="test", year_from=2023, year_to=2024))

        call_kwargs = mock.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["year"] == "2023-2024"

    async def test_api_key_in_headers(self, provider):
        mock_resp = _mock_json_response({"total": 0, "data": []})

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ) as mock:
            await provider.search(SearchQuery(query="test"))

        call_kwargs = mock.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["x-api-key"] == "test-key"

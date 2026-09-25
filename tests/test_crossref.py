"""Tests for the CrossrefProvider."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from researchforge.integrations.crossref import (
    CrossrefProvider,
    _parse_date_parts,
    _parse_item,
)
from researchforge.integrations.models import SearchQuery

SAMPLE_CROSSREF_RESPONSE = {
    "status": "ok",
    "message": {
        "total-results": 1,
        "items": [
            {
                "DOI": "10.1234/example.2024",
                "URL": "https://doi.org/10.1234/example.2024",
                "title": ["Advances in Neural Information Retrieval"],
                "author": [
                    {
                        "given": "Jane",
                        "family": "Doe",
                        "affiliation": [{"name": "Stanford University"}],
                    },
                    {"given": "John", "family": "Smith", "affiliation": []},
                ],
                "abstract": "<jats:p>This paper surveys neural IR methods.</jats:p>",
                "published-print": {"date-parts": [[2024, 3, 15]]},
                "subject": ["Computer Science", "Information Retrieval"],
                "is-referenced-by-count": 42,
            }
        ],
    },
}


def _mock_json_response(data: object, status_code: int = 200) -> httpx.Response:
    import json

    return httpx.Response(
        status_code=status_code,
        text=json.dumps(data),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://test"),
    )


class TestParseDateParts:
    def test_full_date(self):
        assert _parse_date_parts([[2024, 3, 15]]) == date(2024, 3, 15)

    def test_year_month_only(self):
        assert _parse_date_parts([[2024, 3]]) == date(2024, 3, 1)

    def test_year_only(self):
        assert _parse_date_parts([[2024]]) == date(2024, 1, 1)

    def test_empty(self):
        assert _parse_date_parts([]) is None
        assert _parse_date_parts([[]]) is None


class TestParseItem:
    def test_parse_full_item(self):
        message = SAMPLE_CROSSREF_RESPONSE["message"]
        assert isinstance(message, dict)
        items = message["items"]
        assert isinstance(items, list)
        paper = _parse_item(items[0])
        assert paper is not None
        assert paper.source == "crossref"
        assert paper.source_id == "10.1234/example.2024"
        assert paper.title == "Advances in Neural Information Retrieval"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Jane Doe"
        assert paper.authors[0].affiliation == "Stanford University"
        assert paper.authors[1].name == "John Smith"
        assert paper.authors[1].affiliation is None
        assert paper.published_date == date(2024, 3, 15)
        assert paper.doi == "10.1234/example.2024"
        assert paper.abstract == "This paper surveys neural IR methods."
        assert paper.citation_count == 42
        assert "Computer Science" in paper.categories

    def test_missing_title_returns_none(self):
        assert _parse_item({}) is None
        assert _parse_item({"title": []}) is None

    def test_minimal_item(self):
        paper = _parse_item({"title": ["Minimal"], "DOI": "10.0/min"})
        assert paper is not None
        assert paper.title == "Minimal"
        assert paper.doi == "10.0/min"


class TestCrossrefProvider:
    @pytest.fixture
    def provider(self):
        return CrossrefProvider(timeout=5.0, max_retries=1)

    async def test_name(self, provider):
        assert provider.name == "crossref"

    async def test_search_returns_papers(self, provider):
        mock_resp = _mock_json_response(SAMPLE_CROSSREF_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="neural IR"))

        assert result.provider == "crossref"
        assert result.total_results == 1
        assert len(result.papers) == 1
        assert result.papers[0].doi == "10.1234/example.2024"

    async def test_search_empty(self, provider):
        empty_resp = {"status": "ok", "message": {"total-results": 0, "items": []}}
        mock_resp = _mock_json_response(empty_resp)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="nothing"))

        assert result.total_results == 0
        assert result.papers == []

    async def test_year_filter(self, provider):
        empty_resp = {"status": "ok", "message": {"total-results": 0, "items": []}}
        mock_resp = _mock_json_response(empty_resp)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ) as mock:
            await provider.search(SearchQuery(query="test", year_from=2023, year_to=2024))

        call_kwargs = mock.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert "from-pub-date:2023" in params["filter"]
        assert "until-pub-date:2024" in params["filter"]

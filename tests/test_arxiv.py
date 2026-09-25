"""Tests for the ArxivProvider."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from researchforge.integrations.arxiv import ArxivProvider
from researchforge.integrations.models import SearchQuery

SAMPLE_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <title>Attention Is All You Need: A Survey</title>
    <summary>We survey transformer architectures and their applications.</summary>
    <published>2024-01-15T00:00:00Z</published>
    <author><name>Alice Smith</name></author>
    <author>
      <name>Bob Jones</name>
      <arxiv:affiliation>MIT</arxiv:affiliation>
    </author>
    <category term="cs.AI"/>
    <category term="cs.CL"/>
    <link title="pdf" href="https://arxiv.org/pdf/2401.12345v1"
          rel="related" type="application/pdf"/>
    <arxiv:doi>10.1234/test.2024</arxiv:doi>
  </entry>
</feed>"""

EMPTY_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>"""


def _mock_response(text: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code, text=text, request=httpx.Request("GET", "https://test")
    )


class TestArxivProvider:
    @pytest.fixture
    def provider(self):
        return ArxivProvider(timeout=5.0, max_retries=1)

    async def test_search_returns_papers(self, provider):
        mock_resp = _mock_response(SAMPLE_ATOM_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="transformers"))

        assert result.provider == "arxiv"
        assert result.query == "transformers"
        assert result.total_results == 1
        assert len(result.papers) == 1

        paper = result.papers[0]
        assert paper.source == "arxiv"
        assert paper.source_id == "2401.12345v1"
        assert paper.title == "Attention Is All You Need: A Survey"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Alice Smith"
        assert paper.authors[0].affiliation is None
        assert paper.authors[1].name == "Bob Jones"
        assert paper.authors[1].affiliation == "MIT"
        assert paper.published_date == date(2024, 1, 15)
        assert paper.doi == "10.1234/test.2024"
        assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345v1"
        assert paper.categories == ["cs.AI", "cs.CL"]

    async def test_search_empty_results(self, provider):
        mock_resp = _mock_response(EMPTY_ATOM_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await provider.search(SearchQuery(query="nonexistent"))

        assert result.total_results == 0
        assert result.papers == []

    async def test_search_caps_max_results(self, provider):
        mock_resp = _mock_response(EMPTY_ATOM_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ) as mock:
            await provider.search(SearchQuery(query="test", max_results=100))

        call_kwargs = mock.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["max_results"] == 50

    async def test_name(self, provider):
        assert provider.name == "arxiv"

    async def test_sort_by_date(self, provider):
        mock_resp = _mock_response(EMPTY_ATOM_RESPONSE)

        with patch.object(
            provider, "_request_with_retry", new_callable=AsyncMock, return_value=mock_resp
        ) as mock:
            await provider.search(SearchQuery(query="test", sort_by="date"))

        call_kwargs = mock.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["sortBy"] == "lastUpdatedDate"

"""Tests for the base provider retry/error handling."""

import pytest

from researchforge.integrations.base import (
    ProviderError,
    ResearchProvider,
)
from researchforge.integrations.models import SearchQuery, SearchResponse


class DummyProvider(ResearchProvider):
    @property
    def name(self) -> str:
        return "dummy"

    async def search(self, query: SearchQuery) -> SearchResponse:
        return SearchResponse(provider="dummy", query=query.query, total_results=0, papers=[])


class TestProviderError:
    def test_error_includes_provider_name(self):
        err = ProviderError("arxiv", "something broke")
        assert "arxiv" in str(err)
        assert "something broke" in str(err)
        assert err.provider == "arxiv"


class TestRetryLogic:
    @pytest.fixture
    def provider(self):
        return DummyProvider(timeout=1.0, max_retries=2)

    async def test_provider_properties(self, provider):
        assert provider.name == "dummy"
        assert provider.timeout == 1.0
        assert provider.max_retries == 2

    async def test_dummy_search(self, provider):
        result = await provider.search(SearchQuery(query="test"))
        assert result.provider == "dummy"
        assert result.papers == []

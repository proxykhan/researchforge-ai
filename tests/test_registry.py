"""Tests for the provider registry."""

from researchforge.integrations.base import ProviderError, ResearchProvider
from researchforge.integrations.models import SearchQuery, SearchResponse
from researchforge.integrations.registry import ProviderRegistry


class FakeProvider(ResearchProvider):
    def __init__(self, provider_name: str = "fake") -> None:
        super().__init__()
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    async def search(self, query: SearchQuery) -> SearchResponse:
        return SearchResponse(
            provider=self._name,
            query=query.query,
            total_results=0,
            papers=[],
        )


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry(providers=[])
        provider = FakeProvider("test")
        registry.register(provider)
        assert registry.get("test") is provider

    def test_get_nonexistent(self):
        registry = ProviderRegistry(providers=[])
        assert registry.get("nope") is None

    def test_provider_names(self):
        p1 = FakeProvider("alpha")
        p2 = FakeProvider("beta")
        registry = ProviderRegistry(providers=[p1, p2])
        assert "alpha" in registry.provider_names
        assert "beta" in registry.provider_names

    async def test_search_all(self):
        p1 = FakeProvider("p1")
        p2 = FakeProvider("p2")
        registry = ProviderRegistry(providers=[p1, p2])

        results = await registry.search(SearchQuery(query="test"))
        assert len(results) == 2
        providers_in_results = {r.provider for r in results}
        assert providers_in_results == {"p1", "p2"}

    async def test_search_specific_provider(self):
        p1 = FakeProvider("p1")
        p2 = FakeProvider("p2")
        registry = ProviderRegistry(providers=[p1, p2])

        results = await registry.search(SearchQuery(query="test"), providers=["p1"])
        assert len(results) == 1
        assert results[0].provider == "p1"

    async def test_search_ignores_failures(self):
        p1 = FakeProvider("good")
        p2 = FakeProvider("bad")

        async def fail_search(query: SearchQuery) -> SearchResponse:
            raise ProviderError("bad", "intentional failure")

        p2.search = fail_search  # type: ignore[method-assign]
        registry = ProviderRegistry(providers=[p1, p2])

        results = await registry.search(SearchQuery(query="test"))
        assert len(results) == 1
        assert results[0].provider == "good"

    async def test_search_empty_providers(self):
        registry = ProviderRegistry(providers=[])
        results = await registry.search(SearchQuery(query="test"))
        assert results == []

    async def test_search_unknown_provider_name(self):
        registry = ProviderRegistry(providers=[FakeProvider("real")])
        results = await registry.search(SearchQuery(query="test"), providers=["unknown"])
        assert results == []

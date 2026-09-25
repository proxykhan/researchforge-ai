"""Provider registry for managing research sources."""

from __future__ import annotations

import asyncio

from researchforge.integrations.arxiv import ArxivProvider
from researchforge.integrations.base import ResearchProvider
from researchforge.integrations.crossref import CrossrefProvider
from researchforge.integrations.models import SearchQuery, SearchResponse
from researchforge.integrations.semantic_scholar import SemanticScholarProvider


def create_default_providers() -> list[ResearchProvider]:
    """Create the standard set of research providers."""
    return [
        ArxivProvider(),
        SemanticScholarProvider(),
        CrossrefProvider(),
    ]


class ProviderRegistry:
    """Manages multiple research providers and aggregates results."""

    def __init__(self, providers: list[ResearchProvider] | None = None) -> None:
        self._providers: dict[str, ResearchProvider] = {}
        for p in create_default_providers() if providers is None else providers:
            self.register(p)

    def register(self, provider: ResearchProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ResearchProvider | None:
        return self._providers.get(name)

    @property
    def provider_names(self) -> list[str]:
        return list(self._providers.keys())

    async def search(
        self,
        query: SearchQuery,
        providers: list[str] | None = None,
    ) -> list[SearchResponse]:
        """Search one or more providers concurrently."""
        targets = providers or self.provider_names
        selected = [self._providers[n] for n in targets if n in self._providers]

        if not selected:
            return []

        tasks = [p.search(query) for p in selected]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for result in results:
            if isinstance(result, SearchResponse):
                responses.append(result)

        return responses

"""Shared test fixtures and fakes."""

from __future__ import annotations

from researchforge.integrations.models import PaperResult, SearchQuery, SearchResponse
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

FAKE_USAGE = TokenUsage(input_tokens=10, output_tokens=20)


class FakeLLM(LLMProvider):
    """LLM that returns canned responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_index = 0

    @property
    def name(self) -> str:
        return "fake"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        content = self._responses[self._call_index]
        self._call_index += 1
        return LLMResponse(content=content, model="fake-model", usage=FAKE_USAGE)


class FakeSearchProvider:
    """Mimics a ResearchProvider for registry use."""

    def __init__(self, provider_name: str, papers: list[PaperResult] | None = None) -> None:
        self._name = provider_name
        self._papers = papers or []

    @property
    def name(self) -> str:
        return self._name

    async def search(self, query: SearchQuery) -> SearchResponse:
        return SearchResponse(
            provider=self._name,
            query=query.query,
            total_results=len(self._papers),
            papers=self._papers,
        )

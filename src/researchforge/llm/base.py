"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from researchforge.llm.models import LLMConfig, LLMResponse, Message


class LLMProvider(ABC):
    """Interface that every LLM provider must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'anthropic')."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Send messages to the LLM and return a response."""

"""Data models for LLM interactions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    """A single message in a conversation."""

    role: str
    content: str


@dataclass(frozen=True)
class TokenUsage:
    """Token counts from an LLM response."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM provider."""

    content: str
    model: str
    usage: TokenUsage
    stop_reason: str | None = None


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for an LLM call."""

    model: str = "claude-sonnet-5"
    max_tokens: int = 4096
    temperature: float = 0.3
    system: str | None = None
    stop_sequences: list[str] = field(default_factory=list)

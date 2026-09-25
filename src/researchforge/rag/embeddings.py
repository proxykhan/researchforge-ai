"""Embedding provider abstraction and a lightweight local implementation."""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass


class EmbeddingProvider(ABC):
    """Interface for embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of the output vectors."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""


_WORD_PATTERN = re.compile(r"[a-z0-9]+")

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "not",
        "no",
        "so",
        "if",
        "as",
        "from",
        "we",
        "they",
    }
)


@dataclass
class HashEmbeddingProvider(EmbeddingProvider):
    """Lightweight embedding using feature hashing + TF-IDF-style weighting.

    Good enough for in-memory similarity search during development.
    Replaced by a real embedding model (OpenAI, Voyage, etc.) in production.
    """

    _dimensions: int = 256

    @property
    def name(self) -> str:
        return "hash"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = _tokenize(text)
        if not tokens:
            return [0.0] * self._dimensions

        counts = Counter(tokens)
        vec = [0.0] * self._dimensions

        for token, count in counts.items():
            tf = 1 + math.log(count)
            idx = hash(token) % self._dimensions
            sign = 1 if hash(token + "_sign") % 2 == 0 else -1
            vec[idx] += sign * tf

        magnitude = math.sqrt(sum(v * v for v in vec))
        if magnitude > 0:
            vec = [v / magnitude for v in vec]

        return vec


def _tokenize(text: str) -> list[str]:
    words = _WORD_PATTERN.findall(text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

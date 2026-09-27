"""Instrumentation helpers for agent nodes and service methods.

Wraps functions with OpenTelemetry spans and structured log entries
that record timing, status, and key metrics (paper count, token usage, etc.).
"""

from __future__ import annotations

import functools
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog
from opentelemetry import trace

from researchforge.agents.state import ResearchState

logger = structlog.stdlib.get_logger("researchforge.agents")

T = TypeVar("T")


def traced_agent_node(
    name: str,
) -> Callable[[Callable[..., Awaitable[ResearchState]]], Callable[..., Awaitable[ResearchState]]]:
    """Decorator that wraps an agent node with a tracing span and structured log."""

    def decorator(
        func: Callable[..., Awaitable[ResearchState]],
    ) -> Callable[..., Awaitable[ResearchState]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> ResearchState:
            tracer = trace.get_tracer("researchforge.agents")
            with tracer.start_as_current_span(f"agent.{name}") as span:
                span.set_attribute("agent.name", name)
                start = time.perf_counter()

                logger.info("agent.start", agent=name)

                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start) * 1000
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(exc))
                    logger.error(
                        "agent.error",
                        agent=name,
                        error=str(exc),
                        duration_ms=round(duration_ms, 1),
                    )
                    raise

                duration_ms = (time.perf_counter() - start) * 1000
                span.set_attribute("agent.duration_ms", round(duration_ms, 1))

                _record_result_metrics(span, name, result)

                logger.info(
                    "agent.end",
                    agent=name,
                    duration_ms=round(duration_ms, 1),
                )
                return result

        return wrapper

    return decorator


def _record_result_metrics(span: trace.Span, name: str, result: ResearchState) -> None:
    """Extract domain-specific metrics from agent output and record on the span."""
    papers = result.get("papers")
    if papers is not None:
        span.set_attribute("agent.paper_count", len(papers))

    search_queries = result.get("search_queries")
    if search_queries is not None:
        span.set_attribute("agent.query_count", len(search_queries))

    iteration = result.get("iteration")
    if iteration is not None:
        span.set_attribute("agent.iteration", iteration)

    evaluation = result.get("evaluation")
    if evaluation is not None:
        span.set_attribute("agent.evaluation_score", evaluation.overall_score)

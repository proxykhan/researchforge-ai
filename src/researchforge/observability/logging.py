"""Structured logging configuration using structlog.

Production: JSON lines (machine-parseable, CloudWatch-friendly).
Development: colored, human-readable console output.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def setup_logging(*, json: bool = False, level: str = "INFO") -> None:
    """Configure structlog and stdlib logging for the application.

    Args:
        json: True for JSON output (production), False for console (dev).
        level: Root log level name.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore", "opentelemetry"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(**initial_bindings: Any) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger, optionally pre-bound with context."""
    log: structlog.stdlib.BoundLogger = structlog.get_logger(**initial_bindings)
    return log

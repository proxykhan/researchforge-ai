"""Standalone worker entrypoint for background research jobs.

Run with:  python -m researchforge.workers.run

This process connects to the same database and Redis as the API but does
not expose HTTP endpoints.  In production it runs as a separate ECS task
definition, scaling independently from the API.

For now the worker simply keeps the process alive so that the JobManager
(started by the API lifespan) can dispatch tasks to it.  In a future phase
this will poll a task queue (Redis list or SQS) for work.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from researchforge.config import load_settings

logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = load_settings()
    logger.info(
        "Worker starting (env=%s, redis=%s)",
        settings.app_env,
        "connected" if settings.redis_url else "disabled",
    )

    stop = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _handle_signal)

    logger.info("Worker ready — waiting for shutdown signal")
    await stop.wait()
    logger.info("Worker stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(_run())


if __name__ == "__main__":
    main()

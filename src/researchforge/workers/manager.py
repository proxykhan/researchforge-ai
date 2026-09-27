"""Background job manager with concurrency control and graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_SHUTDOWN_TIMEOUT = 30.0


class JobStatus(StrEnum):
    """Internal lifecycle of a managed background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ManagedJob:
    """Tracks a single background job."""

    id: str
    status: JobStatus = JobStatus.PENDING
    task: asyncio.Task[None] | None = None
    error: str | None = None


@dataclass
class JobManager:
    """Manages background asyncio tasks with concurrency limiting.

    - Limits concurrent jobs via an asyncio.Semaphore.
    - Supports cancellation of individual jobs.
    - Provides graceful shutdown that waits for in-flight work.
    """

    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    shutdown_timeout: float = DEFAULT_SHUTDOWN_TIMEOUT
    _semaphore: asyncio.Semaphore = field(init=False)
    _jobs: dict[str, ManagedJob] = field(default_factory=dict, init=False)
    _running: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    def start(self) -> None:
        self._running = True
        logger.info(
            "JobManager started (max_concurrency=%d)",
            self.max_concurrency,
        )

    def submit(
        self,
        job_id: str,
        coro_fn: Callable[[], Awaitable[None]],
    ) -> ManagedJob:
        """Schedule a background job. Returns the ManagedJob immediately."""
        if not self._running:
            raise RuntimeError("JobManager is not running")
        job = ManagedJob(id=job_id)
        self._jobs[job_id] = job
        job.task = asyncio.create_task(self._run_job(job, coro_fn))
        return job

    def cancel(self, job_id: str) -> bool:
        """Cancel a job. Returns True if cancellation was requested."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            return False
        if job.task is not None and not job.task.done():
            job.task.cancel()
        job.status = JobStatus.CANCELLED
        return True

    def get_job(self, job_id: str) -> ManagedJob | None:
        return self._jobs.get(job_id)

    @property
    def active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
        )

    async def shutdown(self) -> None:
        """Wait for in-flight jobs to finish, then stop accepting new ones."""
        self._running = False
        tasks = [j.task for j in self._jobs.values() if j.task is not None and not j.task.done()]
        if tasks:
            logger.info("Waiting for %d in-flight jobs to complete...", len(tasks))
            _done, pending = await asyncio.wait(tasks, timeout=self.shutdown_timeout)
            for t in pending:
                t.cancel()
            if pending:
                logger.warning(
                    "Force-cancelled %d jobs after %.0fs timeout",
                    len(pending),
                    self.shutdown_timeout,
                )
        logger.info("JobManager shut down")

    async def _run_job(
        self,
        job: ManagedJob,
        coro_fn: Callable[[], Awaitable[None]],
    ) -> None:
        async with self._semaphore:
            if job.status == JobStatus.CANCELLED:
                return
            job.status = JobStatus.RUNNING
            try:
                await coro_fn()
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.COMPLETED
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                logger.info("Job %s cancelled", job.id)
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                logger.exception("Job %s failed", job.id)

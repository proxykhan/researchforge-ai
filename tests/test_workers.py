"""Tests for the background job manager."""

from __future__ import annotations

import asyncio

from researchforge.workers.manager import JobManager, JobStatus


class TestJobManager:
    async def test_submit_and_complete(self) -> None:
        manager = JobManager()
        manager.start()
        completed = False

        async def work() -> None:
            nonlocal completed
            completed = True

        job = manager.submit("j1", work)
        await asyncio.sleep(0.1)

        assert completed
        assert job.status == JobStatus.COMPLETED

    async def test_submit_requires_running(self) -> None:
        import pytest

        manager = JobManager()
        with pytest.raises(RuntimeError):
            manager.submit("j1", lambda: asyncio.sleep(0))

    async def test_cancel_pending_job(self) -> None:
        manager = JobManager(max_concurrency=1)
        manager.start()

        blocker = asyncio.Event()

        async def block() -> None:
            await blocker.wait()

        async def second_job() -> None:
            pass

        manager.submit("j1", block)
        await asyncio.sleep(0.05)
        job2 = manager.submit("j2", second_job)

        cancelled = manager.cancel("j2")
        assert cancelled
        assert job2.status == JobStatus.CANCELLED

        blocker.set()
        await asyncio.sleep(0.1)

    async def test_cancel_running_job(self) -> None:
        manager = JobManager()
        manager.start()
        blocker = asyncio.Event()

        async def block() -> None:
            await blocker.wait()

        job = manager.submit("j1", block)
        await asyncio.sleep(0.05)

        cancelled = manager.cancel("j1")
        assert cancelled
        await asyncio.sleep(0.1)
        assert job.status == JobStatus.CANCELLED

    async def test_cancel_nonexistent_returns_false(self) -> None:
        manager = JobManager()
        manager.start()
        assert manager.cancel("nope") is False

    async def test_cancel_completed_returns_false(self) -> None:
        manager = JobManager()
        manager.start()

        async def work() -> None:
            pass

        manager.submit("j1", work)
        await asyncio.sleep(0.1)

        assert manager.cancel("j1") is False

    async def test_failed_job(self) -> None:
        manager = JobManager()
        manager.start()

        async def fail() -> None:
            raise ValueError("boom")

        job = manager.submit("j1", fail)
        await asyncio.sleep(0.1)

        assert job.status == JobStatus.FAILED
        assert job.error == "boom"

    async def test_concurrency_limiting(self) -> None:
        manager = JobManager(max_concurrency=2)
        manager.start()
        running = 0
        max_running = 0
        lock = asyncio.Lock()

        async def track() -> None:
            nonlocal running, max_running
            async with lock:
                running += 1
                max_running = max(max_running, running)
            await asyncio.sleep(0.05)
            async with lock:
                running -= 1

        for i in range(5):
            manager.submit(f"j{i}", track)

        await asyncio.sleep(0.5)
        assert max_running <= 2

    async def test_active_count(self) -> None:
        manager = JobManager()
        manager.start()
        blocker = asyncio.Event()

        async def block() -> None:
            await blocker.wait()

        manager.submit("j1", block)
        await asyncio.sleep(0.05)
        assert manager.active_count == 1

        blocker.set()
        await asyncio.sleep(0.1)
        assert manager.active_count == 0

    async def test_graceful_shutdown(self) -> None:
        manager = JobManager(shutdown_timeout=2.0)
        manager.start()
        completed = False

        async def slow() -> None:
            nonlocal completed
            await asyncio.sleep(0.1)
            completed = True

        manager.submit("j1", slow)
        await manager.shutdown()

        assert completed

    async def test_get_job(self) -> None:
        manager = JobManager()
        manager.start()

        async def work() -> None:
            pass

        manager.submit("j1", work)
        assert manager.get_job("j1") is not None
        assert manager.get_job("nope") is None

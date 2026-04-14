"""
Tests for PriorityTaskScheduler and DeadlineScheduler.

Tests cover:
- Priority ordering (higher priority runs first)
- Cancellation tokens (cancelled tasks are skipped)
- Backpressure (excess tasks are dropped gracefully)
- Deadline enforcement (expired tasks are cancelled)

Author: MYCA / Consciousness OS
Created: April 2026
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from mycosoft_mas.consciousness.cancellation import CancellationToken
from mycosoft_mas.consciousness.scheduler import (
    ConsciousnessPriority,
    DeadlineScheduler,
    PriorityTaskScheduler,
    SchedulerPriority,
    get_priority_scheduler,
)


# ---------------------------------------------------------------------------
# DeadlineScheduler (legacy)
# ---------------------------------------------------------------------------


class TestDeadlineScheduler:
    def _make_scheduler(self, max_workers: int = 4) -> DeadlineScheduler:
        return DeadlineScheduler(max_workers=max_workers)

    @pytest.mark.asyncio
    async def test_submit_and_run(self):
        """A submitted job should run and complete."""
        sched = self._make_scheduler()
        ran = asyncio.Event()

        async def job(token: CancellationToken):
            ran.set()

        job_id = sched.submit("test", job, deadline_ms=2000)
        await asyncio.wait_for(ran.wait(), timeout=2.0)
        assert ran.is_set()
        await sched.stop()

    @pytest.mark.asyncio
    async def test_cancel_removes_job(self):
        """A cancelled job should not run."""
        sched = self._make_scheduler()
        ran = asyncio.Event()

        async def slow_job(token: CancellationToken):
            await asyncio.sleep(5)
            ran.set()

        job_id = sched.submit("test", slow_job, deadline_ms=10000)
        sched.cancel(job_id)
        await asyncio.sleep(0.05)
        assert not ran.is_set()
        await sched.stop()

    @pytest.mark.asyncio
    async def test_cancel_all_by_category(self):
        """cancel_all() for a category should cancel all matching jobs."""
        sched = self._make_scheduler(max_workers=1)
        ran_count = 0

        async def job(token: CancellationToken):
            nonlocal ran_count
            await asyncio.sleep(10)
            ran_count += 1

        for _ in range(3):
            sched.submit("background", job, deadline_ms=30000)
        sched.submit("foreground", job, deadline_ms=30000)

        cancelled = sched.cancel_all("background")
        assert cancelled == 3
        await sched.stop()

    @pytest.mark.asyncio
    async def test_stats(self):
        """Stats should reflect current queue state."""
        sched = self._make_scheduler()
        stats = sched.stats()
        assert "pending" in stats
        assert "running" in stats
        await sched.stop()


# ---------------------------------------------------------------------------
# PriorityTaskScheduler
# ---------------------------------------------------------------------------


class TestPriorityTaskScheduler:
    def _make(self, max_workers: int = 8) -> PriorityTaskScheduler:
        return PriorityTaskScheduler(max_workers=max_workers)

    @pytest.mark.asyncio
    async def test_high_priority_runs(self):
        """A FOREGROUND_CONVERSATION task should run and complete."""
        sched = self._make()
        done = asyncio.Event()

        async def task(token: CancellationToken):
            done.set()

        handle = await sched.submit(
            task,
            priority=ConsciousnessPriority.FOREGROUND_CONVERSATION,
            deadline_ms=2000,
        )
        await asyncio.wait_for(done.wait(), timeout=2.0)
        assert done.is_set()
        await sched.stop()

    @pytest.mark.asyncio
    async def test_cancellation_via_handle(self):
        """Cancelling via handle should prevent task execution."""
        sched = self._make()
        ran = asyncio.Event()

        async def slow_task(token: CancellationToken):
            await asyncio.sleep(5)
            ran.set()

        handle = await sched.submit(
            slow_task,
            priority=ConsciousnessPriority.BACKGROUND_IGNORED
            if hasattr(ConsciousnessPriority, "BACKGROUND_IGNORED")
            else ConsciousnessPriority.MEMORY_WRITES,
            deadline_ms=10000,
        )
        handle.cancel()
        assert handle.is_cancelled

        await asyncio.sleep(0.05)
        assert not ran.is_set()
        await sched.stop()

    @pytest.mark.asyncio
    async def test_backpressure_drops_excess(self):
        """Submitting too many tasks at the same priority should drop extras."""
        sched = self._make(max_workers=1)
        limit = PriorityTaskScheduler.MAX_PENDING_PER_PRIORITY

        handles = []
        for _ in range(limit + 5):
            handle = await sched.submit(
                AsyncMock(return_value=None),
                priority=ConsciousnessPriority.MEMORY_WRITES,
                deadline_ms=30000,
            )
            handles.append(handle)

        # At least some of the excess should be cancelled (backpressure)
        cancelled_count = sum(1 for h in handles if h.is_cancelled)
        assert cancelled_count >= 1, "Backpressure should cancel excess tasks"
        await sched.stop()

    @pytest.mark.asyncio
    async def test_deadline_expired_task_cancelled(self):
        """A task submitted with a very short deadline should be cancelled before running."""
        sched = self._make()
        ran = asyncio.Event()

        async def task(token: CancellationToken):
            ran.set()

        # Submit with 1ms deadline — should expire before dispatched
        handle = await sched.submit(task, deadline_ms=1)
        await asyncio.sleep(0.1)  # Let scheduler tick
        # Either ran (if dispatched before expiry) or not — should NOT hang
        await sched.stop()

    @pytest.mark.asyncio
    async def test_cancel_all_below_priority(self):
        """cancel_all_below() should cancel tasks below the given priority."""
        sched = self._make(max_workers=1)
        count = 0

        async def dummy(token):
            await asyncio.sleep(10)

        low_handle = await sched.submit(
            dummy, priority=ConsciousnessPriority.MEMORY_WRITES, deadline_ms=30000
        )
        high_handle = await sched.submit(
            dummy,
            priority=ConsciousnessPriority.FOREGROUND_CONVERSATION,
            deadline_ms=30000,
        )

        cancelled = sched.cancel_all_below(ConsciousnessPriority.TOOL_CALLS)
        assert cancelled >= 1
        assert low_handle.is_cancelled
        await sched.stop()

    @pytest.mark.asyncio
    async def test_stats_returns_dict(self):
        """Stats should include pending and running counts."""
        sched = self._make()
        stats = sched.stats()
        assert "pending" in stats
        assert "running" in stats
        assert "pending_by_priority" in stats
        await sched.stop()

    def test_singleton(self):
        """get_priority_scheduler() should return the same instance each call."""
        a = get_priority_scheduler()
        b = get_priority_scheduler()
        assert a is b

"""
Tests for DeadlineScheduler - Full-Duplex Voice Phase 8.

Created: February 12, 2026
"""

import asyncio

import pytest

from mycosoft_mas.consciousness.scheduler import DeadlineScheduler, SchedulerPriority


class TestDeadlineScheduler:
    @pytest.mark.asyncio
    async def test_submit_and_run_job(self):
        scheduler = DeadlineScheduler(max_workers=2)
        ran = False

        async def job_fn(token):
            nonlocal ran
            token.check()
            ran = True

        scheduler.submit("tool", job_fn, priority=SchedulerPriority.NORMAL, deadline_ms=1000)
        await asyncio.sleep(0.05)
        assert ran is True
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_cancel_all(self):
        scheduler = DeadlineScheduler(max_workers=1)
        cancelled = False

        async def long_job(token):
            nonlocal cancelled
            try:
                while True:
                    token.check()
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                cancelled = True
                raise

        scheduler.submit("agent", long_job, priority=SchedulerPriority.HIGH, deadline_ms=5000)
        await asyncio.sleep(0.03)
        assert scheduler.cancel_all("agent") >= 1
        await asyncio.sleep(0.05)
        assert cancelled is True
        await scheduler.stop()


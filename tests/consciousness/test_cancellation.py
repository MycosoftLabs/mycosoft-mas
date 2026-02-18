"""
Tests for cancellation primitives - Full-Duplex Voice Phase 2 (minimal).

Created: February 12, 2026
"""

import asyncio

import pytest

from mycosoft_mas.consciousness.cancellation import CancellationToken, TaskRegistry


class TestCancellationToken:
    def test_cancel_sets_state(self):
        token = CancellationToken()
        assert token.is_cancelled is False
        token.cancel()
        assert token.is_cancelled is True
        assert token.cancelled_at is not None

    def test_check_raises_when_cancelled(self):
        token = CancellationToken()
        token.cancel()
        with pytest.raises(asyncio.CancelledError):
            token.check()


class TestTaskRegistry:
    @pytest.mark.asyncio
    async def test_register_and_cleanup(self):
        registry = TaskRegistry()

        async def job():
            await asyncio.sleep(0.01)
            return 1

        handle = registry.register(asyncio.create_task(job()), category="tool")
        assert handle.task_id in registry.active()
        await handle.task
        await asyncio.sleep(0.01)
        assert handle.task_id not in registry.active()

    @pytest.mark.asyncio
    async def test_cancel_all_by_category(self):
        registry = TaskRegistry()
        cancelled = 0

        async def long_job():
            nonlocal cancelled
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                cancelled += 1
                raise

        h1 = registry.register(asyncio.create_task(long_job()), category="tool")
        h2 = registry.register(asyncio.create_task(long_job()), category="agent")

        count = registry.cancel_all(category="tool")
        await asyncio.sleep(0.02)

        assert count == 1
        assert h1.task.cancelled() or cancelled >= 1
        assert h2.task.cancelled() is False
        registry.cancel_all()

    @pytest.mark.asyncio
    async def test_submit_backpressure_limits(self):
        registry = TaskRegistry()
        original = dict(TaskRegistry.MAX_PER_CATEGORY)
        TaskRegistry.MAX_PER_CATEGORY["tool"] = 2

        async def long_job():
            await asyncio.sleep(1)

        try:
            h1 = registry.submit("tool", long_job())
            h2 = registry.submit("tool", long_job())
            h3 = registry.submit("tool", long_job())
            assert h1 is not None
            assert h2 is not None
            assert h3 is None
        finally:
            TaskRegistry.MAX_PER_CATEGORY = original
            registry.cancel_all()


"""
Cancellation primitives for full-duplex consciousness runtime.

Phase 2 (minimal): cooperative cancellation with task registry.
Created: February 12, 2026
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


class CancellationToken:
    """Cooperative cancellation token for long-running async work."""

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._cancelled_at: Optional[datetime] = None

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def cancelled_at(self) -> Optional[datetime]:
        return self._cancelled_at

    def cancel(self) -> None:
        if not self._event.is_set():
            self._cancelled_at = datetime.now()
            self._event.set()

    async def wait_cancelled(self) -> None:
        await self._event.wait()

    def check(self) -> None:
        if self._event.is_set():
            raise asyncio.CancelledError("Cancellation token triggered")


@dataclass
class TaskHandle:
    """Registered async task with cooperative cancellation token."""

    task_id: str
    category: str
    task: asyncio.Task
    token: CancellationToken
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def cancel(self) -> None:
        self.token.cancel()
        if not self.task.done():
            self.task.cancel()

    @property
    def is_done(self) -> bool:
        return self.task.done()


class TaskRegistry:
    """Minimal task registry for cancellation and visibility."""

    MAX_PER_CATEGORY = {
        "conversation": 2,
        "tool": 5,
        "agent": 10,
        "background": 20,
    }

    def __init__(self) -> None:
        self._handles: Dict[str, TaskHandle] = {}
        self._counter = 0

    def _category_count(self, category: str) -> int:
        return sum(1 for h in self._handles.values() if h.category == category and not h.is_done)

    def can_accept(self, category: str) -> bool:
        limit = self.MAX_PER_CATEGORY.get(category, 10)
        return self._category_count(category) < limit

    def register(
        self,
        task: asyncio.Task,
        category: str,
        token: Optional[CancellationToken] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskHandle:
        self._counter += 1
        task_id = f"{category}-{self._counter}"
        handle = TaskHandle(
            task_id=task_id,
            category=category,
            task=task,
            token=token or CancellationToken(),
            metadata=metadata or {},
        )
        self._handles[task_id] = handle
        task.add_done_callback(lambda _: self._handles.pop(task_id, None))
        return handle

    def submit(
        self,
        category: str,
        coro: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskHandle]:
        """
        Submit a coroutine with backpressure limits by category.

        Returns None if rejected due to category limits.
        """
        if not self.can_accept(category):
            close = getattr(coro, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            return None
        task = asyncio.create_task(coro)
        return self.register(task=task, category=category, metadata=metadata)

    def cancel(self, task_id: str) -> bool:
        handle = self._handles.get(task_id)
        if not handle:
            return False
        handle.cancel()
        return True

    def cancel_all(self, category: Optional[str] = None) -> int:
        handles = list(self._handles.values())
        if category is not None:
            handles = [h for h in handles if h.category == category]
        for handle in handles:
            handle.cancel()
        return len(handles)

    def active(self, category: Optional[str] = None) -> Dict[str, TaskHandle]:
        if category is None:
            return dict(self._handles)
        return {task_id: h for task_id, h in self._handles.items() if h.category == category}


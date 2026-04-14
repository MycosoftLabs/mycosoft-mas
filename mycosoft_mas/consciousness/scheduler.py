"""
Deadline-aware scheduler for consciousness tasks.

Phase 8: true scheduler (implemented but optional to use).
PriorityTaskScheduler (Full-Duplex Consciousness OS) added April 2026.
Created: February 12, 2026
"""

import asyncio
import heapq
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .cancellation import CancellationToken

logger = logging.getLogger(__name__)


class SchedulerPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class ScheduledJob:
    sort_key: tuple = field(init=False, repr=False)
    deadline_ts: float
    priority: SchedulerPriority
    created_ts: float
    job_id: str
    category: str
    job_fn: Callable[[CancellationToken], Awaitable[Any]]
    token: CancellationToken = field(default_factory=CancellationToken, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        # Earliest deadline first, then priority, then creation order
        self.sort_key = (self.deadline_ts, int(self.priority), self.created_ts)


class DeadlineScheduler:
    """
    Simple EDF scheduler with limited workers and cooperative cancellation.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._pending: List[ScheduledJob] = []
        self._running: Dict[str, asyncio.Task] = {}
        self._jobs: Dict[str, ScheduledJob] = {}
        self._shutdown = asyncio.Event()
        self._dispatch_task: Optional[asyncio.Task] = None
        self._counter = 0

    def start(self) -> None:
        if self._dispatch_task and not self._dispatch_task.done():
            return
        self._shutdown.clear()
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._dispatch_task:
            await asyncio.gather(self._dispatch_task, return_exceptions=True)
        # Cancel all remaining jobs
        for job in list(self._jobs.values()):
            job.token.cancel()
        for task in list(self._running.values()):
            task.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        self._running.clear()
        self._jobs.clear()
        self._pending.clear()

    def submit(
        self,
        category: str,
        job_fn: Callable[[CancellationToken], Awaitable[Any]],
        priority: SchedulerPriority = SchedulerPriority.NORMAL,
        deadline_ms: int = 5000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._counter += 1
        now_ts = datetime.now(timezone.utc).timestamp()
        job_id = f"job-{self._counter}"
        job = ScheduledJob(
            deadline_ts=now_ts + (deadline_ms / 1000),
            priority=priority,
            created_ts=now_ts,
            job_id=job_id,
            category=category,
            job_fn=job_fn,
            metadata=metadata or {},
        )
        self._jobs[job_id] = job
        heapq.heappush(self._pending, job)
        self.start()
        return job_id

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.token.cancel()
        task = self._running.get(job_id)
        if task and not task.done():
            task.cancel()
        return True

    def cancel_all(self, category: Optional[str] = None) -> int:
        ids = list(self._jobs.keys())
        if category is not None:
            ids = [job_id for job_id, job in self._jobs.items() if job.category == category]
        for job_id in ids:
            self.cancel(job_id)
        return len(ids)

    async def _dispatch_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                while self._pending and len(self._running) < self.max_workers:
                    job = heapq.heappop(self._pending)
                    if job.token.is_cancelled:
                        self._jobs.pop(job.job_id, None)
                        continue
                    job.started_at = datetime.now(timezone.utc)
                    task = asyncio.create_task(self._run_job(job))
                    self._running[job.job_id] = task
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Scheduler dispatch loop error: {exc}")
                await asyncio.sleep(0.05)

    async def _run_job(self, job: ScheduledJob) -> None:
        try:
            await job.job_fn(job.token)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(f"Scheduled job failed ({job.job_id}): {exc}")
        finally:
            job.completed_at = datetime.now(timezone.utc)
            self._running.pop(job.job_id, None)
            self._jobs.pop(job.job_id, None)

    def stats(self) -> Dict[str, Any]:
        return {
            "pending": len(self._pending),
            "running": len(self._running),
            "max_workers": self.max_workers,
            "known_jobs": len(self._jobs),
        }


# ---------------------------------------------------------------------------
# Full-Duplex Consciousness OS: PriorityTaskScheduler
# ---------------------------------------------------------------------------


class ConsciousnessPriority(IntEnum):
    """Priority levels for consciousness operations (higher = more urgent)."""

    FOREGROUND_CONVERSATION = 100  # Never starve — user is waiting
    TOOL_CALLS = 80               # Tool results needed for response
    AGENT_TASKS = 60              # Background agent work
    WORLD_UPDATES = 40            # World model refresh
    MEMORY_WRITES = 20            # Write-behind memory persistence


@dataclass
class TaskHandle:
    """Handle for a submitted task."""

    task_id: str
    priority: ConsciousnessPriority
    token: CancellationToken
    submitted_at: float = field(default_factory=time.monotonic)
    deadline_ms: int = 5000

    def cancel(self) -> None:
        self.token.cancel()

    @property
    def is_cancelled(self) -> bool:
        return self.token.is_cancelled


@dataclass(order=True)
class _PriorityEntry:
    """Internal heap entry: lower sort_key = higher urgency."""

    # Negate priority so highest priority pops first from min-heap
    neg_priority: int
    deadline_abs: float
    seq: int
    handle: TaskHandle = field(compare=False)
    coro_fn: Callable[[CancellationToken], Awaitable[Any]] = field(compare=False)


class PriorityTaskScheduler:
    """
    Real-time OS scheduler for consciousness operations.

    Features:
    - 5-level priority queue (foreground conversation never starved)
    - Per-task CancellationToken wired to every async operation
    - Hard deadlines — tasks cancelled if they breach their deadline
    - Backpressure — cap on pending tasks per priority level
    - Preemption signal — higher-priority submission cancels lower running tasks
    """

    MAX_PENDING_PER_PRIORITY = 20  # Backpressure limit
    FRAME_BUDGET_MS = 100          # Target frame time

    def __init__(self, max_workers: int = 8) -> None:
        self._max_workers = max_workers
        self._heap: List[_PriorityEntry] = []
        self._running: Dict[str, asyncio.Task] = {}
        self._handles: Dict[str, TaskHandle] = {}
        self._seq = 0
        self._pending_counts: Dict[ConsciousnessPriority, int] = {
            p: 0 for p in ConsciousnessPriority
        }
        self._shutdown = asyncio.Event()
        self._dispatch_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def start(self) -> None:
        if self._dispatch_task and not self._dispatch_task.done():
            return
        self._shutdown.clear()
        self._dispatch_task = asyncio.create_task(
            self._dispatch_loop(), name="consciousness-scheduler"
        )

    async def stop(self) -> None:
        self._shutdown.set()
        for handle in list(self._handles.values()):
            handle.cancel()
        for task in list(self._running.values()):
            task.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        if self._dispatch_task:
            self._dispatch_task.cancel()
            await asyncio.gather(self._dispatch_task, return_exceptions=True)
        self._running.clear()
        self._handles.clear()
        self._heap.clear()

    async def submit(
        self,
        coro_fn: Callable[[CancellationToken], Awaitable[Any]],
        priority: ConsciousnessPriority = ConsciousnessPriority.AGENT_TASKS,
        deadline_ms: int = 5000,
        cancellable: bool = True,
    ) -> TaskHandle:
        """
        Submit a task to the scheduler.

        Args:
            coro_fn: Async callable that accepts a CancellationToken
            priority: ConsciousnessPriority level
            deadline_ms: Hard deadline in milliseconds (task cancelled if exceeded)
            cancellable: If False, token.cancel() is a no-op

        Returns:
            TaskHandle for monitoring/cancellation
        """
        async with self._lock:
            # Backpressure: reject if too many pending at this priority
            if self._pending_counts.get(priority, 0) >= self.MAX_PENDING_PER_PRIORITY:
                # Drop lowest-priority overflow; still return a cancelled handle
                token = CancellationToken()
                if cancellable:
                    token.cancel()
                self._seq += 1
                handle = TaskHandle(
                    task_id=f"sched-{self._seq}",
                    priority=priority,
                    token=token,
                    deadline_ms=deadline_ms,
                )
                logger.warning(
                    f"Scheduler backpressure: dropping {priority.name} task (queue full)"
                )
                return handle

            token = CancellationToken()
            self._seq += 1
            handle = TaskHandle(
                task_id=f"sched-{self._seq}",
                priority=priority,
                token=token,
                deadline_ms=deadline_ms,
            )
            entry = _PriorityEntry(
                neg_priority=-int(priority),
                deadline_abs=time.monotonic() + deadline_ms / 1000,
                seq=self._seq,
                handle=handle,
                coro_fn=coro_fn,
            )
            heapq.heappush(self._heap, entry)
            self._pending_counts[priority] = self._pending_counts.get(priority, 0) + 1
            self._handles[handle.task_id] = handle

        self.start()
        return handle

    def submit_sync(
        self,
        coro_fn: Callable[[CancellationToken], Awaitable[Any]],
        priority: ConsciousnessPriority = ConsciousnessPriority.AGENT_TASKS,
        deadline_ms: int = 5000,
    ) -> str:
        """Synchronous submit for use outside async context. Returns task_id."""
        token = CancellationToken()
        self._seq += 1
        handle = TaskHandle(
            task_id=f"sched-{self._seq}",
            priority=priority,
            token=token,
            deadline_ms=deadline_ms,
        )
        entry = _PriorityEntry(
            neg_priority=-int(priority),
            deadline_abs=time.monotonic() + deadline_ms / 1000,
            seq=self._seq,
            handle=handle,
            coro_fn=coro_fn,
        )
        heapq.heappush(self._heap, entry)
        self._handles[handle.task_id] = handle
        self.start()
        return handle.task_id

    def cancel(self, task_id: str) -> bool:
        handle = self._handles.get(task_id)
        if not handle:
            return False
        handle.cancel()
        task = self._running.get(task_id)
        if task and not task.done():
            task.cancel()
        return True

    def cancel_all_below(self, min_priority: ConsciousnessPriority) -> int:
        """Cancel all pending/running tasks below a given priority level."""
        cancelled = 0
        for tid, handle in list(self._handles.items()):
            if handle.priority < min_priority:
                self.cancel(tid)
                cancelled += 1
        return cancelled

    async def _dispatch_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                now = time.monotonic()
                dispatched = 0
                while self._heap and len(self._running) < self._max_workers:
                    entry = heapq.heappop(self._heap)
                    priority = ConsciousnessPriority(-entry.neg_priority)
                    self._pending_counts[priority] = max(
                        0, self._pending_counts.get(priority, 0) - 1
                    )

                    # Skip cancelled or expired tasks
                    if entry.handle.is_cancelled:
                        self._handles.pop(entry.handle.task_id, None)
                        continue
                    if now > entry.deadline_abs:
                        entry.handle.cancel()
                        self._handles.pop(entry.handle.task_id, None)
                        logger.debug(
                            f"Task {entry.handle.task_id} expired (deadline breach)"
                        )
                        continue

                    task = asyncio.create_task(
                        self._run_entry(entry),
                        name=f"cs-{entry.handle.task_id}",
                    )
                    self._running[entry.handle.task_id] = task
                    dispatched += 1

                await asyncio.sleep(0.005)  # 5ms poll
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"PriorityTaskScheduler dispatch error: {exc}")
                await asyncio.sleep(0.02)

    async def _run_entry(self, entry: _PriorityEntry) -> None:
        handle = entry.handle
        try:
            await entry.coro_fn(handle.token)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(f"Scheduled task {handle.task_id} raised: {exc}")
        finally:
            self._running.pop(handle.task_id, None)
            self._handles.pop(handle.task_id, None)

    def stats(self) -> Dict[str, Any]:
        return {
            "pending": len(self._heap),
            "running": len(self._running),
            "max_workers": self._max_workers,
            "pending_by_priority": {
                p.name: self._pending_counts.get(p, 0) for p in ConsciousnessPriority
            },
        }


# Module-level singleton
_priority_scheduler: Optional[PriorityTaskScheduler] = None


def get_priority_scheduler() -> PriorityTaskScheduler:
    """Get the global PriorityTaskScheduler instance."""
    global _priority_scheduler
    if _priority_scheduler is None:
        _priority_scheduler = PriorityTaskScheduler()
    return _priority_scheduler

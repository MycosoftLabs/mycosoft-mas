"""
Deadline-aware scheduler for consciousness tasks.

Phase 8: true scheduler (implemented but optional to use).
Created: February 12, 2026
"""

import asyncio
import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Awaitable, Callable, Dict, List, Optional

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


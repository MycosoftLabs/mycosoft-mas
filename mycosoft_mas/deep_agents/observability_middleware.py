"""
Prometheus metrics helpers for Deep Agent lifecycle.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Histogram

DEEP_AGENT_TASKS_TOTAL = Counter(
    "myca_deep_agent_tasks_total",
    "Total deep agent tasks",
    labelnames=("agent_name", "status"),
)

DEEP_AGENT_TASK_DURATION_SECONDS = Histogram(
    "myca_deep_agent_task_duration_seconds",
    "Deep agent task duration in seconds",
    labelnames=("agent_name",),
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)


@contextmanager
def observe_task_duration(agent_name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = max(0.0, time.perf_counter() - start)
        DEEP_AGENT_TASK_DURATION_SECONDS.labels(agent_name=agent_name).observe(elapsed)


def increment_task_counter(agent_name: str, status: str) -> None:
    DEEP_AGENT_TASKS_TOTAL.labels(agent_name=agent_name, status=status).inc()

"""Fleet + per-agent RPM token buckets for Agent100."""

from __future__ import annotations

import threading
import time

from mycosoft_mas.agent100.constants import agent_rpm, fleet_rpm


class _Bucket:
    def __init__(self, rate_per_minute: int) -> None:
        self.rate = max(1, rate_per_minute)
        self.tokens = float(self.rate)
        self.capacity = float(self.rate)
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(self.capacity, self.tokens + (elapsed / 60.0) * self.rate)

    def acquire(self, tokens: float = 1.0, timeout_s: float = 120.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            time.sleep(0.05)
        return False


class Agent100Supervisor:
    """Shared fleet limiter + per-agent buckets."""

    def __init__(self) -> None:
        self._fleet = _Bucket(fleet_rpm())
        self._per_agent: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _agent_bucket(self, agent_id: str) -> _Bucket:
        with self._lock:
            if agent_id not in self._per_agent:
                self._per_agent[agent_id] = _Bucket(agent_rpm())
            return self._per_agent[agent_id]

    def acquire_request_slot(self, agent_id: str, timeout_s: float = 120.0) -> bool:
        if not self._fleet.acquire(1.0, timeout_s=timeout_s):
            return False
        return self._agent_bucket(agent_id).acquire(1.0, timeout_s=timeout_s)

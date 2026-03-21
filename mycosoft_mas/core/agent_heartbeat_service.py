"""
Agent Heartbeat Service — March 19, 2026

The missing bridge between the MAS agent runtime and the visibility layer.

Problem: Agents run in the runner, topology viewer listens to Redis agents:status,
but nothing publishes heartbeats. Dashboard shows zeros. Morgan sees nothing.

Solution: This service runs as a background task, polls agent runner state every
15 seconds, and publishes real status to Redis channels that the topology viewer,
dashboard, and WebSocket streams already subscribe to.

NO MOCK DATA — All metrics come from the real agent runner and system health.
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger(__name__)

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "15"))


class AgentMetrics:
    """Tracks per-agent runtime metrics across cycles."""

    def __init__(self):
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.insights_generated: int = 0
        self.knowledge_added: int = 0
        self.last_cycle_time: Optional[str] = None
        self.last_cycle_duration_ms: float = 0
        self.consecutive_errors: int = 0
        self.status: str = "idle"
        self.last_error: Optional[str] = None
        self.first_seen: str = datetime.now(timezone.utc).isoformat()
        self.cycle_count: int = 0

    def record_cycle(self, cycle_data: Dict[str, Any]):
        """Record a completed cycle."""
        self.cycle_count += 1
        self.tasks_completed += cycle_data.get("tasks_processed", 0)
        self.insights_generated += cycle_data.get("insights_generated", 0)
        self.knowledge_added += cycle_data.get("knowledge_added", 0)
        self.last_cycle_time = datetime.now(timezone.utc).isoformat()

        if cycle_data.get("status") == "error":
            self.tasks_failed += 1
            self.consecutive_errors += 1
            self.status = "error" if self.consecutive_errors >= 3 else "degraded"
            errors = cycle_data.get("errors", [])
            self.last_error = errors[-1] if errors else "Unknown error"
        else:
            self.consecutive_errors = 0
            self.status = "active"
            self.last_error = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "insights_generated": self.insights_generated,
            "knowledge_added": self.knowledge_added,
            "last_cycle_time": self.last_cycle_time,
            "last_cycle_duration_ms": self.last_cycle_duration_ms,
            "consecutive_errors": self.consecutive_errors,
            "status": self.status,
            "last_error": self.last_error,
            "first_seen": self.first_seen,
            "cycle_count": self.cycle_count,
        }


class AgentHeartbeatService:
    """
    Bridges the agent runner to Redis pub/sub channels.

    Publishes to:
    - agents:status — per-agent heartbeats (consumed by topology_stream.py)
    - system:health — aggregate system metrics (consumed by system_health_ws.py)
    - tasks:progress — task completion events (consumed by task_progress_ws.py)
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._agent_metrics: Dict[str, AgentMetrics] = defaultdict(AgentMetrics)
        self._start_time = time.time()
        self._total_heartbeats = 0
        self._redis_connected = False
        self._last_cycle_snapshot: Dict[str, Any] = {}

    @property
    def agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Expose metrics for dashboard/orchestrator API to read."""
        return self._agent_metrics

    def get_system_summary(self) -> Dict[str, Any]:
        """Get aggregate system metrics — used by dashboard router."""
        total_tasks = sum(m.tasks_completed for m in self._agent_metrics.values())
        total_errors = sum(m.tasks_failed for m in self._agent_metrics.values())
        total_insights = sum(m.insights_generated for m in self._agent_metrics.values())
        active_count = sum(1 for m in self._agent_metrics.values() if m.status == "active")
        degraded_count = sum(1 for m in self._agent_metrics.values() if m.status == "degraded")
        error_count = sum(1 for m in self._agent_metrics.values() if m.status == "error")

        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
        except Exception:
            cpu_usage = 0
            memory_usage = 0

        uptime_seconds = int(time.time() - self._start_time)

        return {
            "total_agents": len(self._agent_metrics),
            "active_agents": active_count,
            "degraded_agents": degraded_count,
            "error_agents": error_count,
            "total_tasks_completed": total_tasks,
            "total_errors": total_errors,
            "total_insights": total_insights,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "uptime_seconds": uptime_seconds,
            "heartbeat_count": self._total_heartbeats,
            "redis_connected": self._redis_connected,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def start(self):
        """Start the heartbeat background loop."""
        if self._running:
            logger.warning("Heartbeat service already running")
            return

        self._running = True
        self._start_time = time.time()
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Agent heartbeat service started (interval={HEARTBEAT_INTERVAL}s)")

    async def stop(self):
        """Stop the heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent heartbeat service stopped")

    async def _heartbeat_loop(self):
        """Main heartbeat loop — polls runner, publishes to Redis."""
        # Initial delay to let the runner start
        await asyncio.sleep(5)

        while self._running:
            try:
                await self._collect_and_publish()
                self._total_heartbeats += 1
            except Exception as e:
                logger.error(f"Heartbeat cycle error: {e}")

            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _collect_and_publish(self):
        """Collect agent status from runner and publish to Redis."""
        from mycosoft_mas.core.agent_runner import get_agent_runner

        runner = get_agent_runner()
        runner_status = await runner.get_status()

        # Update metrics from runner's recent cycles
        for cycle_data in runner_status.get("recent_cycles", []):
            agent_id = cycle_data.get("agent_id", "unknown")
            if agent_id not in self._last_cycle_snapshot or self._last_cycle_snapshot.get(
                agent_id
            ) != cycle_data.get("cycle_id"):
                self._agent_metrics[agent_id].record_cycle(cycle_data)
                self._last_cycle_snapshot[agent_id] = cycle_data.get("cycle_id")

        # Ensure all runner agents have metrics entries
        for agent in runner._agents:
            agent_id = getattr(agent, "agent_id", getattr(agent, "name", str(id(agent))))
            if agent_id not in self._agent_metrics:
                self._agent_metrics[agent_id] = AgentMetrics()
                self._agent_metrics[agent_id].status = "idle"

        # Publish to Redis
        try:
            from mycosoft_mas.realtime.redis_pubsub import (
                Channel,
                get_client,
                publish_agent_status,
            )

            client = await get_client()
            self._redis_connected = client.is_connected()

            if not self._redis_connected:
                logger.warning("Redis not connected — skipping heartbeat publish")
                return

            # Publish per-agent status to agents:status channel
            for agent_id, metrics in self._agent_metrics.items():
                await publish_agent_status(
                    agent_id=agent_id,
                    status=metrics.status,
                    details={
                        **metrics.to_dict(),
                        "heartbeat_seq": self._total_heartbeats,
                    },
                    source="heartbeat_service",
                )

            # Publish aggregate system health to system:health channel
            summary = self.get_system_summary()
            await client.publish(
                Channel.SYSTEM_HEALTH.value,
                {
                    "event": "system_heartbeat",
                    **summary,
                },
                source="heartbeat_service",
            )

            # Publish task completions to tasks:progress channel
            for cycle_data in runner_status.get("recent_cycles", []):
                if cycle_data.get("status") == "completed":
                    await client.publish(
                        Channel.TASK_PROGRESS.value,
                        {
                            "event": "task_completed",
                            "agent_id": cycle_data.get("agent_id"),
                            "agent_name": cycle_data.get("agent_name"),
                            "tasks_processed": cycle_data.get("tasks_processed", 0),
                            "summary": cycle_data.get("summary", ""),
                            "completed_at": cycle_data.get("completed_at"),
                        },
                        source="heartbeat_service",
                    )

        except ImportError:
            logger.debug("Redis pub/sub not available — heartbeat service running in local mode")
            self._redis_connected = False
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            self._redis_connected = False


# Singleton
_heartbeat_service: Optional[AgentHeartbeatService] = None


def get_heartbeat_service() -> AgentHeartbeatService:
    """Get the global heartbeat service singleton."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = AgentHeartbeatService()
    return _heartbeat_service

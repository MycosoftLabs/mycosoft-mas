"""
MYCA 24/7 Agent Runner
Continuous agent operation with work compilation into knowledge bases.

Isolation guarantees (Sep 23 / Sep 24 2026):
- Cycle work never blocks the uvicorn request path without a hard timeout
- Background tasks are tracked and cancelled on stop (no duplicate loops)
- Disk / webhook I/O is best-effort with timeouts
- Cycle history is bounded so get_status stays cheap
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import httpx

logger = logging.getLogger(__name__)

NAS_BASE_PATH = os.getenv("NAS_STORAGE_PATH", "/mnt/nas/mycosoft/mas")
LOCAL_BASE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./data/agent_work")

# Prefer local unless explicitly opted into NAS (hung CIFS wedges the event loop).
_use_nas = os.getenv("AGENT_RUNNER_USE_NAS", "0") == "1" and os.path.exists(NAS_BASE_PATH)
STORAGE_PATH = Path(NAS_BASE_PATH if _use_nas else LOCAL_BASE_PATH)

# Hard caps so a bad agent cannot stall :8001.
DEFAULT_CYCLE_TIMEOUT_SEC = float(os.getenv("AGENT_CYCLE_TIMEOUT_SEC", "15"))
DEFAULT_SAVE_TIMEOUT_SEC = float(os.getenv("AGENT_CYCLE_SAVE_TIMEOUT_SEC", "2"))
MAX_CYCLES_RETAINED = int(os.getenv("AGENT_RUNNER_MAX_CYCLES", "200"))
MAX_INSIGHTS_RETAINED = int(os.getenv("AGENT_RUNNER_MAX_INSIGHTS", "200"))
MAX_NOTIFICATIONS_RETAINED = int(os.getenv("AGENT_RUNNER_MAX_NOTIFICATIONS", "200"))


@dataclass
class WorkCycle:
    """Represents a single agent work cycle."""

    cycle_id: str
    agent_id: str
    agent_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    tasks_processed: int = 0
    insights_generated: int = 0
    knowledge_added: int = 0
    errors: Optional[List[str]] = None
    summary: str = ""

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class AgentInsight:
    """An insight discovered by an agent."""

    insight_id: str
    agent_id: str
    agent_name: str
    category: str
    title: str
    description: str
    confidence: float
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    actionable: bool = False
    priority: str = "normal"  # low, normal, high, critical

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class AdminNotification:
    """Notification to be sent to Morgan (super admin)."""

    notification_id: str
    timestamp: str
    type: str  # task_complete, insight, error, news, discovery
    title: str
    message: str
    agent: str
    priority: str = "normal"  # low, normal, high, critical
    requires_action: bool = False
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class AgentCycleRunner:
    """
    Runs agents continuously in cycles, 24/7 operation.

    Features:
    - Continuous agent cycling with per-cycle timeouts
    - Work compilation into databases
    - Knowledge base updates
    - Local (or opt-in NAS) storage for monitoring
    - Admin notifications for Morgan
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.running = False
        self.cycles: "OrderedDict[str, WorkCycle]" = OrderedDict()
        self.insights: List[AgentInsight] = []
        self.notifications: List[AdminNotification] = []
        self._agents: List[Any] = []
        self._cycle_interval = float(
            self.config.get("cycle_interval", os.getenv("AGENT_CYCLE_INTERVAL_SEC", "300"))
        )
        self._cycle_timeout = float(
            self.config.get("cycle_timeout", DEFAULT_CYCLE_TIMEOUT_SEC)
        )
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._cycle_task: Optional[asyncio.Task] = None
        self._notification_task: Optional[asyncio.Task] = None
        self._generation = 0  # bumped on each start to invalidate stale loops

        self._ensure_storage()

    def configure(self, **kwargs: Any) -> None:
        """Update runtime knobs (interval/timeout/agents) without recreating singleton."""
        if "cycle_interval" in kwargs and kwargs["cycle_interval"] is not None:
            self._cycle_interval = float(kwargs["cycle_interval"])
            self.config["cycle_interval"] = self._cycle_interval
        if "cycle_timeout" in kwargs and kwargs["cycle_timeout"] is not None:
            self._cycle_timeout = float(kwargs["cycle_timeout"])
            self.config["cycle_timeout"] = self._cycle_timeout

    def _ensure_storage(self):
        """Ensure storage directories exist (sync, local path preferred)."""
        dirs = [
            STORAGE_PATH / "cycles",
            STORAGE_PATH / "insights",
            STORAGE_PATH / "notifications",
            STORAGE_PATH / "knowledge",
            STORAGE_PATH / "workloads",
            STORAGE_PATH / "wisdom",
        ]
        for d in dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning("Could not create runner storage %s: %s", d, exc)
        logger.info("Agent storage initialized at: %s", STORAGE_PATH)

    def _retain(self, mapping: "OrderedDict[str, WorkCycle]", key: str, value: WorkCycle) -> None:
        mapping[key] = value
        while len(mapping) > MAX_CYCLES_RETAINED:
            mapping.popitem(last=False)

    async def start(self, agents: Optional[List[Any]] = None):
        """Start the continuous agent runner."""
        if self.running:
            logger.warning("Agent runner already running")
            return

        # Cancel any leftover tasks from a previous generation.
        await self._cancel_background_tasks()

        self.running = True
        self._generation += 1
        generation = self._generation
        self._agents = agents or []

        logger.info(
            "Starting 24/7 Agent Runner with %s agents (interval=%ss timeout=%ss gen=%s)",
            len(self._agents),
            self._cycle_interval,
            self._cycle_timeout,
            generation,
        )

        self._notification_task = asyncio.create_task(
            self._notification_worker(generation), name="agent-runner-notifications"
        )
        self._cycle_task = asyncio.create_task(
            self._run_cycles(generation), name="agent-runner-cycles"
        )

        # Non-blocking admin notify (queued)
        try:
            await self.notify_admin(
                type="system",
                title="MYCA System Online",
                message=(
                    f"24/7 Agent Runner started with {len(self._agents)} agents. "
                    "All systems operational."
                ),
                agent="MYCA",
                priority="high",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Startup notify skipped: %s", exc)

    async def stop(self):
        """Stop the agent runner and cancel background tasks."""
        self.running = False
        self._generation += 1
        logger.info("Stopping 24/7 Agent Runner")

        try:
            await self.notify_admin(
                type="system",
                title="MYCA System Shutdown",
                message="24/7 Agent Runner shutting down.",
                agent="MYCA",
                priority="critical",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Shutdown notify skipped: %s", exc)

        await self._cancel_background_tasks()

    async def _cancel_background_tasks(self) -> None:
        tasks = [t for t in (self._cycle_task, self._notification_task) if t is not None]
        self._cycle_task = None
        self._notification_task = None
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_cycles(self, generation: int):
        """Main cycle loop - runs agents continuously with yields between agents."""
        try:
            while self.running and generation == self._generation:
                cycle_start = datetime.now()

                # Snapshot agents so supervisor swaps mid-cycle don't confuse us.
                agents = list(self._agents)
                for agent in agents:
                    if not self.running or generation != self._generation:
                        break
                    try:
                        await self._run_agent_cycle(agent)
                    except Exception as e:  # noqa: BLE001
                        name = getattr(agent, "name", agent.__class__.__name__)
                        logger.error("Error in agent cycle %s: %s", name, e)
                        try:
                            await self.notify_admin(
                                type="error",
                                title=f"Agent Error: {name}",
                                message=str(e)[:500],
                                agent=str(name),
                                priority="high",
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    # Yield to uvicorn request handlers between agents.
                    await asyncio.sleep(0)

                elapsed = (datetime.now() - cycle_start).total_seconds()
                wait_time = max(0.0, self._cycle_interval - elapsed)
                if wait_time > 0 and self.running and generation == self._generation:
                    # Sleep in chunks so stop() is responsive.
                    remaining = wait_time
                    while remaining > 0 and self.running and generation == self._generation:
                        step = min(1.0, remaining)
                        await asyncio.sleep(step)
                        remaining -= step
        except asyncio.CancelledError:
            logger.info("Agent runner cycle loop cancelled (gen=%s)", generation)
            raise

    async def _run_agent_cycle(self, agent) -> WorkCycle:
        """Run a single cycle for an agent with a hard timeout."""
        agent_name = getattr(agent, "name", None) or agent.__class__.__name__
        agent_id = getattr(agent, "agent_id", "unknown")
        cycle_id = f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        cycle = WorkCycle(
            cycle_id=cycle_id,
            agent_id=str(agent_id),
            agent_name=str(agent_name),
            started_at=datetime.now().isoformat(),
        )
        self._retain(self.cycles, cycle_id, cycle)

        logger.debug("Starting cycle %s", cycle_id)

        try:
            if hasattr(agent, "run_cycle"):
                result = await asyncio.wait_for(
                    agent.run_cycle(), timeout=self._cycle_timeout
                )
                if isinstance(result, dict):
                    cycle.tasks_processed = int(result.get("tasks_processed", 0) or 0)
                    cycle.insights_generated = int(result.get("insights_generated", 0) or 0)
                    cycle.knowledge_added = int(result.get("knowledge_added", 0) or 0)
                    cycle.summary = str(result.get("summary", "Cycle completed"))[:1000]

                    insights = result.get("insights") or []
                    for insight_data in insights[:5]:
                        if not isinstance(insight_data, dict):
                            continue
                        insight = AgentInsight(
                            insight_id=(
                                f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                                f"{len(self.insights)}"
                            ),
                            agent_id=cycle.agent_id,
                            agent_name=str(agent_name),
                            category=str(insight_data.get("category", "general")),
                            title=str(insight_data.get("title", "Insight")),
                            description=str(insight_data.get("description", "")),
                            confidence=float(insight_data.get("confidence", 0.5) or 0.5),
                            timestamp=datetime.now().isoformat(),
                            data=insight_data.get("data")
                            if isinstance(insight_data.get("data"), dict)
                            else {},
                            actionable=bool(insight_data.get("actionable", False)),
                            priority=str(insight_data.get("priority", "normal")),
                        )
                        self.insights.append(insight)
                        if len(self.insights) > MAX_INSIGHTS_RETAINED:
                            self.insights = self.insights[-MAX_INSIGHTS_RETAINED:]
                        if insight.priority in ("high", "critical"):
                            await self.notify_admin(
                                type="insight",
                                title=insight.title,
                                message=insight.description[:500],
                                agent=str(agent_name),
                                priority=insight.priority,
                                data=insight.data,
                            )
                else:
                    cycle.tasks_processed = 1
                    cycle.summary = "Cycle completed (non-dict result)"

            elif hasattr(agent, "process_tasks"):
                await asyncio.wait_for(agent.process_tasks(), timeout=self._cycle_timeout)
                cycle.tasks_processed = 1
                cycle.summary = "Legacy task processing completed"

            else:
                cycle.summary = "Agent idle - no work method defined"

            cycle.status = "completed"

        except asyncio.TimeoutError:
            cycle.status = "timeout"
            cycle.errors.append(f"cycle_timeout_{self._cycle_timeout}s")
            cycle.summary = f"Timed out after {self._cycle_timeout}s"
            logger.warning("Cycle %s timed out after %ss", cycle_id, self._cycle_timeout)
        except Exception as e:  # noqa: BLE001
            cycle.status = "error"
            cycle.errors.append(str(e)[:500])
            cycle.summary = f"Error: {str(e)[:300]}"
            logger.error("Cycle %s failed: %s", cycle_id, e)

        cycle.completed_at = datetime.now().isoformat()

        # Best-effort disk persist — never block the loop for NAS/disk stalls.
        try:
            await asyncio.wait_for(self._save_cycle(cycle), timeout=DEFAULT_SAVE_TIMEOUT_SEC)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cycle save skipped: %s", exc)

        return cycle

    async def _save_cycle(self, cycle: WorkCycle):
        """Save work cycle to local/NAS storage."""
        filepath = STORAGE_PATH / "cycles" / f"{cycle.cycle_id}.json"
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(asdict(cycle), indent=2))

    async def _save_insight(self, insight: AgentInsight):
        """Save insight to storage."""
        filepath = STORAGE_PATH / "insights" / f"{insight.insight_id}.json"
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(asdict(insight), indent=2))

    async def notify_admin(
        self,
        type: str,
        title: str,
        message: str,
        agent: str,
        priority: str = "normal",
        requires_action: bool = False,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Queue a notification for Morgan (super admin)."""
        notification = AdminNotification(
            notification_id=(
                f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.notifications)}"
            ),
            timestamp=datetime.now().isoformat(),
            type=type,
            title=title,
            message=message,
            agent=agent,
            priority=priority,
            requires_action=requires_action,
            data=data or {},
        )
        self.notifications.append(notification)
        if len(self.notifications) > MAX_NOTIFICATIONS_RETAINED:
            self.notifications = self.notifications[-MAX_NOTIFICATIONS_RETAINED:]
        try:
            self._notification_queue.put_nowait(notification)
        except asyncio.QueueFull:
            logger.warning("Notification queue full; dropping %s", notification.notification_id)

    async def _notification_worker(self, generation: int):
        """Process notifications and send to admin."""
        try:
            while self.running and generation == self._generation:
                try:
                    notification = await asyncio.wait_for(
                        self._notification_queue.get(), timeout=10
                    )
                except asyncio.TimeoutError:
                    continue

                try:
                    filepath = (
                        STORAGE_PATH / "notifications" / f"{notification.notification_id}.json"
                    )
                    async with aiofiles.open(filepath, "w") as f:
                        await f.write(json.dumps(asdict(notification), indent=2))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Notification save skipped: %s", exc)

                logger.info(
                    "[ADMIN NOTIFICATION] %s: %s",
                    notification.priority.upper(),
                    notification.title,
                )

                try:
                    await asyncio.wait_for(
                        self._send_notification_webhook(notification), timeout=5
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Notification webhook skipped: %s", exc)
        except asyncio.CancelledError:
            logger.info("Notification worker cancelled (gen=%s)", generation)
            raise
        except Exception as e:  # noqa: BLE001
            logger.error("Notification worker error: %s", e)

    async def _send_notification_webhook(self, notification: AdminNotification) -> None:
        """Send notification via webhook to configured endpoints."""
        webhook_urls = os.getenv("NOTIFICATION_WEBHOOK_URLS", "").split(",")
        webhook_urls = [url.strip() for url in webhook_urls if url.strip()]

        if not webhook_urls:
            return

        payload = {
            "id": notification.notification_id,
            "priority": notification.priority,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.timestamp,
            "source_agent": notification.agent,
            "data": notification.data,
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            for webhook_url in webhook_urls:
                try:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if response.status_code in (200, 201, 202, 204):
                        logger.info("Notification webhook delivered to %s", webhook_url)
                    else:
                        logger.warning(
                            "Webhook returned %s: %s", response.status_code, webhook_url
                        )
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to send webhook to %s: %s", webhook_url, e)

    async def get_status(self) -> Dict[str, Any]:
        """Get current runner status (bounded payload)."""
        recent = list(self.cycles.values())[-10:]
        return {
            "running": self.running,
            "agents": len(self._agents),
            "agent_ids": [
                str(getattr(a, "agent_id", getattr(a, "name", a.__class__.__name__)))
                for a in self._agents[:50]
            ],
            "total_cycles": len(self.cycles),
            "total_insights": len(self.insights),
            "total_notifications": len(self.notifications),
            "storage_path": str(STORAGE_PATH),
            "cycle_interval": self._cycle_interval,
            "cycle_timeout": self._cycle_timeout,
            "generation": self._generation,
            "recent_cycles": [asdict(c) for c in recent],
            "recent_insights": [asdict(i) for i in self.insights[-10:]],
            "recent_notifications": [asdict(n) for n in self.notifications[-10:]],
        }

    async def compile_wisdom(self) -> Dict[str, Any]:
        """Compile accumulated insights into wisdom/knowledge."""
        wisdom = {
            "compiled_at": datetime.now().isoformat(),
            "total_insights": len(self.insights),
            "by_agent": {},
            "by_category": {},
            "actionable_items": [],
            "key_discoveries": [],
        }

        for insight in self.insights:
            if insight.agent_name not in wisdom["by_agent"]:
                wisdom["by_agent"][insight.agent_name] = []
            wisdom["by_agent"][insight.agent_name].append(
                {
                    "title": insight.title,
                    "description": insight.description,
                    "timestamp": insight.timestamp,
                }
            )

            if insight.category not in wisdom["by_category"]:
                wisdom["by_category"][insight.category] = []
            wisdom["by_category"][insight.category].append(insight.title)

            if insight.actionable:
                wisdom["actionable_items"].append(
                    {
                        "title": insight.title,
                        "agent": insight.agent_name,
                        "priority": insight.priority,
                    }
                )

            if insight.confidence > 0.8:
                wisdom["key_discoveries"].append(
                    {
                        "title": insight.title,
                        "description": insight.description,
                        "confidence": insight.confidence,
                    }
                )

        filepath = STORAGE_PATH / "wisdom" / f"wisdom_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            async with aiofiles.open(filepath, "w") as f:
                await f.write(json.dumps(wisdom, indent=2))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Wisdom save skipped: %s", exc)

        return wisdom


_runner: Optional[AgentCycleRunner] = None


def get_agent_runner() -> AgentCycleRunner:
    """Get the global agent runner singleton."""
    global _runner
    if _runner is None:
        _runner = AgentCycleRunner()
    return _runner


async def start_24_7_operation(agents: Optional[List[Any]] = None):
    """Start 24/7 agent operation."""
    runner = get_agent_runner()
    await runner.start(agents)
    return runner

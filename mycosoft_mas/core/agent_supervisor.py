"""
Agent Supervisor — March 19, 2026

Lifecycle management for MAS agents. Monitors heartbeat data, detects dead/degraded
agents, attempts restarts, and publishes lifecycle events to Redis for the topology
viewer and dashboard.

Problem: Agents could fail silently. Nobody detects or restarts them. Morgan sees nothing.

Solution: This supervisor runs as a background task, watches heartbeat metrics,
and takes corrective action when agents go dark.

NO MOCK DATA — All decisions based on real heartbeat service metrics.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# How often the supervisor checks (seconds)
SUPERVISOR_INTERVAL = 30

# How many consecutive errors before attempting restart
ERROR_THRESHOLD = 3

# How long since last cycle before marking agent as unresponsive (seconds)
UNRESPONSIVE_TIMEOUT = 180


class AgentSupervisor:
    """
    Monitors agent health and manages lifecycle.

    Responsibilities:
    - Detect dead/unresponsive agents from heartbeat data
    - Mark agents as degraded/error in heartbeat service
    - Attempt agent restart via runner reload
    - Publish lifecycle events (spawned, restarted, failed) to Redis
    - Track restart attempts to prevent restart loops
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._restart_attempts: Dict[str, int] = {}
        self._max_restart_attempts = 3
        self._restart_cooldown: Dict[str, float] = {}
        self._cooldown_seconds = 300  # 5 minutes between restart attempts
        self._lifecycle_events: List[Dict[str, Any]] = []

    @property
    def lifecycle_events(self) -> List[Dict[str, Any]]:
        """Recent lifecycle events for dashboard display."""
        return self._lifecycle_events[-100:]  # Keep last 100

    async def start(self):
        """Start the supervisor background loop."""
        if self._running:
            logger.warning("Agent supervisor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._supervisor_loop())
        logger.info(f"Agent supervisor started (interval={SUPERVISOR_INTERVAL}s)")

        await self._publish_lifecycle_event(
            "supervisor_started",
            agent_id="supervisor",
            details={"interval": SUPERVISOR_INTERVAL},
        )

    async def stop(self):
        """Stop the supervisor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent supervisor stopped")

    async def _supervisor_loop(self):
        """Main supervision loop."""
        await asyncio.sleep(30)  # Let system stabilize before first check

        while self._running:
            try:
                await self._check_agents()
            except Exception as e:
                logger.error(f"Supervisor check error: {e}")

            await asyncio.sleep(SUPERVISOR_INTERVAL)

    async def _check_agents(self):
        """Check all agents for health issues."""
        try:
            from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
        except ImportError:
            return

        hb_service = get_heartbeat_service()
        now = time.time()

        for agent_id, metrics in hb_service.agent_metrics.items():
            # Check for consecutive errors
            if metrics.consecutive_errors >= ERROR_THRESHOLD:
                await self._handle_error_agent(agent_id, metrics)

            # Check for unresponsive agents (no cycle in timeout period)
            elif metrics.last_cycle_time:
                try:
                    last_cycle = datetime.fromisoformat(
                        metrics.last_cycle_time.replace("Z", "+00:00")
                    )
                    elapsed = (datetime.now(timezone.utc) - last_cycle).total_seconds()
                    if elapsed > UNRESPONSIVE_TIMEOUT:
                        await self._handle_unresponsive_agent(agent_id, elapsed)
                except (ValueError, TypeError):
                    pass

    async def _handle_error_agent(self, agent_id: str, metrics):
        """Handle an agent with too many consecutive errors."""
        logger.warning(
            f"Agent {agent_id} has {metrics.consecutive_errors} consecutive errors: "
            f"{metrics.last_error}"
        )

        # Check cooldown
        if not self._can_restart(agent_id):
            return

        # Attempt restart
        await self._attempt_restart(agent_id, reason=f"consecutive_errors={metrics.consecutive_errors}")

    async def _handle_unresponsive_agent(self, agent_id: str, elapsed_seconds: float):
        """Handle an unresponsive agent."""
        logger.warning(
            f"Agent {agent_id} unresponsive for {elapsed_seconds:.0f}s"
        )

        # Update heartbeat status
        try:
            from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
            hb = get_heartbeat_service()
            if agent_id in hb.agent_metrics:
                hb.agent_metrics[agent_id].status = "unresponsive"
        except Exception:
            pass

        await self._publish_lifecycle_event(
            "agent_unresponsive",
            agent_id=agent_id,
            details={"elapsed_seconds": elapsed_seconds},
        )

    def _can_restart(self, agent_id: str) -> bool:
        """Check if we can attempt a restart (cooldown + max attempts)."""
        # Check max attempts
        attempts = self._restart_attempts.get(agent_id, 0)
        if attempts >= self._max_restart_attempts:
            return False

        # Check cooldown
        last_restart = self._restart_cooldown.get(agent_id, 0)
        if time.time() - last_restart < self._cooldown_seconds:
            return False

        return True

    async def _attempt_restart(self, agent_id: str, reason: str):
        """Attempt to restart an agent via the runner."""
        self._restart_attempts[agent_id] = self._restart_attempts.get(agent_id, 0) + 1
        self._restart_cooldown[agent_id] = time.time()
        attempt = self._restart_attempts[agent_id]

        logger.info(f"Attempting restart of {agent_id} (attempt {attempt}/{self._max_restart_attempts}): {reason}")

        try:
            from mycosoft_mas.core.agent_runner import get_agent_runner
            from mycosoft_mas.core.runner_agent_loader import (
                _instantiate_native_agent,
                LoadedRunnerAgent,
            )
            from mycosoft_mas.core.agent_registry import get_agent_registry

            runner = get_agent_runner()
            registry = get_agent_registry()
            definition = registry.get(agent_id)

            if not definition:
                logger.error(f"Cannot restart {agent_id}: not found in registry")
                await self._publish_lifecycle_event(
                    "agent_restart_failed",
                    agent_id=agent_id,
                    details={"reason": "not_in_registry"},
                )
                return

            # Try to instantiate a fresh agent
            try:
                delegate = _instantiate_native_agent(definition)
                new_agent = LoadedRunnerAgent(
                    definition=definition, delegate=delegate, mode="native"
                )
            except Exception as e:
                new_agent = LoadedRunnerAgent(
                    definition=definition, delegate=None, mode="fallback", error=str(e)
                )

            # Replace in runner's agent list
            for i, existing in enumerate(runner._agents):
                existing_id = getattr(existing, "agent_id", None)
                if existing_id == agent_id:
                    runner._agents[i] = new_agent
                    break
            else:
                # Agent not in runner, add it
                runner._agents.append(new_agent)

            # Reset heartbeat metrics
            from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
            hb = get_heartbeat_service()
            if agent_id in hb.agent_metrics:
                hb.agent_metrics[agent_id].consecutive_errors = 0
                hb.agent_metrics[agent_id].status = "restarted"

            await self._publish_lifecycle_event(
                "agent_restarted",
                agent_id=agent_id,
                details={"attempt": attempt, "reason": reason, "mode": new_agent.mode},
            )

            logger.info(f"Successfully restarted {agent_id} in {new_agent.mode} mode")

        except Exception as e:
            logger.error(f"Failed to restart {agent_id}: {e}")
            await self._publish_lifecycle_event(
                "agent_restart_failed",
                agent_id=agent_id,
                details={"attempt": attempt, "error": str(e)},
            )

    async def _publish_lifecycle_event(
        self,
        event_type: str,
        agent_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Publish a lifecycle event to Redis and local store."""
        event = {
            "event": event_type,
            "agent_id": agent_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._lifecycle_events.append(event)

        # Publish to Redis agents:status channel
        try:
            from mycosoft_mas.realtime.redis_pubsub import get_client, Channel

            client = await get_client()
            if client.is_connected():
                await client.publish(
                    Channel.AGENTS_STATUS.value,
                    {
                        "agent_id": agent_id,
                        "status": event_type,
                        "details": details or {},
                    },
                    source="agent_supervisor",
                )
        except Exception as e:
            logger.debug(f"Could not publish lifecycle event to Redis: {e}")

        # Log to event ledger
        try:
            from mycosoft_mas.myca.event_ledger.ledger_writer import get_ledger
            ledger = get_ledger()
            ledger.log_tool_call(
                agent="supervisor",
                tool_name=event_type,
                args_hash=f"agent:{agent_id}",
                result_status="success",
                elapsed_ms=0,
            )
        except Exception:
            pass


# Singleton
_supervisor: Optional[AgentSupervisor] = None


def get_supervisor() -> AgentSupervisor:
    """Get the global agent supervisor singleton."""
    global _supervisor
    if _supervisor is None:
        _supervisor = AgentSupervisor()
    return _supervisor

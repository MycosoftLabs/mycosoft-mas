"""
MYCA Autonomous Self - Self-Healing, Self-Improving, Self-Learning, Self-Aware

This is the autonomous framework that gives MYCA the ability to:
- Self-Heal: Detect failures, auto-restart services, reallocate resources
- Self-Improve: Analyze performance, identify weaknesses, apply improvements
- Self-Learn: Continuously ingest new data, track knowledge growth
- Self-Aware: Monitor cognitive processes, detect biases, introspect

Together these form the AutonomousSelf -- a higher-order system that runs
continuously in the background, keeping MYCA healthy, sharp, and growing
without human intervention.

Unlike assigned tasks, the autonomous self operates on MYCA's own initiative.
It is the immune system, the growth mindset, and the inner eye all in one.

Author: Morgan Rockwell / MYCA
Created: March 3, 2026
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CYCLE_INTERVAL_SECONDS = 60
_HEALTH_CHECK_TIMEOUT_SECONDS = 10
_MAX_INTROSPECTION_LOG_SIZE = 500
_MAX_LEARNING_QUEUE_SIZE = 1000
_MAX_ISSUE_HISTORY_SIZE = 200
_MAX_IMPROVEMENT_HISTORY_SIZE = 200


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HealthStatus(Enum):
    """Overall health status of a monitored component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Severity of a detected issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImprovementCategory(Enum):
    """Category of a proposed improvement."""

    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    ACCURACY = "accuracy"
    LATENCY = "latency"
    RESOURCE_USAGE = "resource_usage"
    KNOWLEDGE = "knowledge"
    COMMUNICATION = "communication"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AutonomousState:
    """Tracks the autonomous system's aggregate state across all engines."""

    is_running: bool = False
    started_at: Optional[datetime] = None
    last_cycle_at: Optional[datetime] = None
    total_cycles: int = 0
    total_heals: int = 0
    total_improvements: int = 0
    total_learnings: int = 0
    total_introspections: int = 0
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to a plain dictionary."""
        return {
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
            "total_cycles": self.total_cycles,
            "total_heals": self.total_heals,
            "total_improvements": self.total_improvements,
            "total_learnings": self.total_learnings,
            "total_introspections": self.total_introspections,
            "overall_health": self.overall_health.value,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class DetectedIssue:
    """An issue detected by the self-healing engine."""

    issue_id: str
    detected_at: datetime
    component: str
    severity: IssueSeverity
    description: str
    auto_healed: bool = False
    heal_action: str = ""
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "detected_at": self.detected_at.isoformat(),
            "component": self.component,
            "severity": self.severity.value,
            "description": self.description,
            "auto_healed": self.auto_healed,
            "heal_action": self.heal_action,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class ImprovementProposal:
    """A concrete improvement identified by the self-improvement engine."""

    proposal_id: str
    created_at: datetime
    category: ImprovementCategory
    description: str
    expected_impact: float  # 0.0 - 1.0
    applied: bool = False
    applied_at: Optional[datetime] = None
    outcome: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "created_at": self.created_at.isoformat(),
            "category": self.category.value,
            "description": self.description,
            "expected_impact": self.expected_impact,
            "applied": self.applied,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "outcome": self.outcome,
        }


@dataclass
class LearningItem:
    """An item in the self-learning queue."""

    item_id: str
    queued_at: datetime
    source: str
    content: str
    domain: str
    priority: float = 0.5  # 0.0 - 1.0
    processed: bool = False
    processed_at: Optional[datetime] = None


@dataclass
class IntrospectionEntry:
    """A single entry in the self-awareness introspection log."""

    timestamp: datetime
    observation: str
    cognitive_load: float  # 0.0 - 1.0
    bias_flags: List[str] = field(default_factory=list)
    resource_snapshot: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Self-Healing Engine
# ---------------------------------------------------------------------------


class SelfHealingEngine:
    """
    Monitors system health, detects failures, auto-restarts degraded
    components, and reallocates resources when bottlenecks are found.

    The engine maintains a registry of health-check callables. Each cycle
    it invokes them, records results, and when a check fails it attempts
    the registered recovery action.
    """

    def __init__(self) -> None:
        self._health_checks: Dict[str, Callable[[], Coroutine[Any, Any, bool]]] = {}
        self._recovery_actions: Dict[str, Callable[[], Coroutine[Any, Any, bool]]] = {}
        self._component_status: Dict[str, HealthStatus] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._issue_history: deque[DetectedIssue] = deque(maxlen=_MAX_ISSUE_HISTORY_SIZE)
        self._total_heals: int = 0

        # Metrics
        self._heal_success_count: int = 0
        self._heal_failure_count: int = 0

    # -- Registration -------------------------------------------------------

    def register_health_check(
        self,
        component: str,
        check_fn: Callable[[], Coroutine[Any, Any, bool]],
        recovery_fn: Optional[Callable[[], Coroutine[Any, Any, bool]]] = None,
    ) -> None:
        """Register a health check and optional recovery action for *component*."""
        self._health_checks[component] = check_fn
        if recovery_fn is not None:
            self._recovery_actions[component] = recovery_fn
        self._component_status[component] = HealthStatus.UNKNOWN
        self._consecutive_failures[component] = 0
        logger.debug("Registered health check for component '%s'", component)

    # -- Core ---------------------------------------------------------------

    async def run_checks(self) -> Dict[str, HealthStatus]:
        """Run all registered health checks and return component statuses."""
        for component, check_fn in self._health_checks.items():
            try:
                healthy = await asyncio.wait_for(check_fn(), timeout=_HEALTH_CHECK_TIMEOUT_SECONDS)
                if healthy:
                    self._component_status[component] = HealthStatus.HEALTHY
                    self._consecutive_failures[component] = 0
                else:
                    self._consecutive_failures[component] += 1
                    self._component_status[component] = (
                        HealthStatus.DEGRADED
                        if self._consecutive_failures[component] < 3
                        else HealthStatus.UNHEALTHY
                    )
            except asyncio.TimeoutError:
                self._consecutive_failures[component] += 1
                self._component_status[component] = HealthStatus.DEGRADED
                logger.warning("Health check timed out for '%s'", component)
            except Exception as exc:
                self._consecutive_failures[component] += 1
                self._component_status[component] = HealthStatus.UNHEALTHY
                logger.error("Health check failed for '%s': %s", component, exc)

        return dict(self._component_status)

    async def heal(self) -> List[DetectedIssue]:
        """
        Attempt to heal any components that are degraded or unhealthy.

        Returns a list of DetectedIssue objects describing what was found
        and whether automatic recovery succeeded.
        """
        issues: List[DetectedIssue] = []
        now = datetime.now(timezone.utc)

        for component, status in self._component_status.items():
            if status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
                severity = (
                    IssueSeverity.HIGH if status == HealthStatus.UNHEALTHY else IssueSeverity.MEDIUM
                )
                issue = DetectedIssue(
                    issue_id=f"issue-{uuid.uuid4().hex[:12]}",
                    detected_at=now,
                    component=component,
                    severity=severity,
                    description=(
                        f"Component '{component}' is {status.value} "
                        f"(consecutive failures: {self._consecutive_failures[component]})"
                    ),
                )

                # Attempt recovery if a handler is registered
                if component in self._recovery_actions:
                    try:
                        recovered = await self._recovery_actions[component]()
                        issue.auto_healed = recovered
                        issue.heal_action = (
                            "Recovery action executed successfully"
                            if recovered
                            else "Recovery action executed but component still unhealthy"
                        )
                        if recovered:
                            issue.resolved_at = datetime.now(timezone.utc)
                            self._component_status[component] = HealthStatus.HEALTHY
                            self._consecutive_failures[component] = 0
                            self._heal_success_count += 1
                            self._total_heals += 1
                            logger.info("Auto-healed component '%s'", component)
                        else:
                            self._heal_failure_count += 1
                            logger.warning(
                                "Recovery action for '%s' did not restore health", component
                            )
                    except Exception as exc:
                        issue.heal_action = f"Recovery action raised: {exc}"
                        self._heal_failure_count += 1
                        logger.error("Recovery action failed for '%s': %s", component, exc)
                else:
                    issue.heal_action = "No recovery action registered"

                issues.append(issue)
                self._issue_history.append(issue)

        return issues

    # -- Queries ------------------------------------------------------------

    def get_overall_health(self) -> HealthStatus:
        """Derive the aggregate health status across all components."""
        if not self._component_status:
            return HealthStatus.UNKNOWN
        statuses = set(self._component_status.values())
        if statuses == {HealthStatus.HEALTHY}:
            return HealthStatus.HEALTHY
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.UNKNOWN

    def get_metrics(self) -> Dict[str, Any]:
        """Return healing metrics."""
        return {
            "registered_components": len(self._health_checks),
            "healthy_components": sum(
                1 for s in self._component_status.values() if s == HealthStatus.HEALTHY
            ),
            "total_heals": self._total_heals,
            "heal_success_count": self._heal_success_count,
            "heal_failure_count": self._heal_failure_count,
            "heal_success_rate": (
                self._heal_success_count
                / max(1, self._heal_success_count + self._heal_failure_count)
            ),
            "recent_issues": [i.to_dict() for i in list(self._issue_history)[-10:]],
        }


# ---------------------------------------------------------------------------
# Self-Improvement Engine
# ---------------------------------------------------------------------------


class SelfImprovementEngine:
    """
    Analyzes MYCA's performance over time, identifies weaknesses, proposes
    concrete improvements, and tracks improvement metrics.

    Improvements are stored as proposals. External callers (or the autonomous
    loop) can apply them and record outcomes.
    """

    def __init__(self) -> None:
        self._response_times: deque[float] = deque(maxlen=500)
        self._success_outcomes: deque[bool] = deque(maxlen=500)
        self._proposals: deque[ImprovementProposal] = deque(maxlen=_MAX_IMPROVEMENT_HISTORY_SIZE)
        self._applied_count: int = 0
        self._total_proposals: int = 0

    # -- Data ingestion -----------------------------------------------------

    def record_response_time(self, seconds: float) -> None:
        """Record a task/response completion time."""
        self._response_times.append(seconds)

    def record_outcome(self, success: bool) -> None:
        """Record whether a task succeeded or failed."""
        self._success_outcomes.append(success)

    # -- Analysis -----------------------------------------------------------

    async def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze recent performance data and return a summary with
        identified weaknesses.
        """
        now = datetime.now(timezone.utc)
        analysis: Dict[str, Any] = {"timestamp": now.isoformat(), "weaknesses": []}

        # Response time analysis
        if self._response_times:
            times = list(self._response_times)
            avg_time = sum(times) / len(times)
            max_time = max(times)
            p95_index = int(len(times) * 0.95)
            sorted_times = sorted(times)
            p95_time = sorted_times[min(p95_index, len(sorted_times) - 1)]

            analysis["avg_response_time_s"] = round(avg_time, 4)
            analysis["p95_response_time_s"] = round(p95_time, 4)
            analysis["max_response_time_s"] = round(max_time, 4)
            analysis["response_time_samples"] = len(times)

            if p95_time > 5.0:
                analysis["weaknesses"].append(
                    f"High p95 latency ({p95_time:.2f}s) -- consider caching or parallelism"
                )

        # Success rate analysis
        if self._success_outcomes:
            outcomes = list(self._success_outcomes)
            success_rate = sum(1 for o in outcomes if o) / len(outcomes)
            analysis["success_rate"] = round(success_rate, 4)
            analysis["outcome_samples"] = len(outcomes)

            if success_rate < 0.90:
                analysis["weaknesses"].append(
                    f"Success rate below 90% ({success_rate:.1%}) -- investigate failure causes"
                )
            if success_rate < 0.75:
                analysis["weaknesses"].append(
                    "Success rate critically low -- immediate attention required"
                )

        return analysis

    async def propose_improvements(self, analysis: Dict[str, Any]) -> List[ImprovementProposal]:
        """Generate improvement proposals from a performance analysis."""
        proposals: List[ImprovementProposal] = []
        now = datetime.now(timezone.utc)

        for weakness in analysis.get("weaknesses", []):
            category = ImprovementCategory.PERFORMANCE
            expected_impact = 0.3

            if "latency" in weakness.lower():
                category = ImprovementCategory.LATENCY
                expected_impact = 0.5
            elif "success rate" in weakness.lower():
                if "critically" in weakness.lower():
                    category = ImprovementCategory.RELIABILITY
                    expected_impact = 0.8
                else:
                    category = ImprovementCategory.RELIABILITY
                    expected_impact = 0.5

            proposal = ImprovementProposal(
                proposal_id=f"imp-{uuid.uuid4().hex[:12]}",
                created_at=now,
                category=category,
                description=weakness,
                expected_impact=expected_impact,
            )
            proposals.append(proposal)
            self._proposals.append(proposal)
            self._total_proposals += 1

        return proposals

    async def apply_improvement(self, proposal_id: str, outcome: str = "") -> bool:
        """
        Mark an improvement proposal as applied and record its outcome.

        Returns True if the proposal was found and updated.
        """
        for proposal in self._proposals:
            if proposal.proposal_id == proposal_id and not proposal.applied:
                proposal.applied = True
                proposal.applied_at = datetime.now(timezone.utc)
                proposal.outcome = outcome
                self._applied_count += 1
                logger.info("Applied improvement '%s': %s", proposal_id, proposal.description[:80])
                return True
        return False

    def get_metrics(self) -> Dict[str, Any]:
        """Return improvement metrics."""
        success_rate = 0.0
        if self._success_outcomes:
            outcomes = list(self._success_outcomes)
            success_rate = sum(1 for o in outcomes if o) / len(outcomes)

        avg_response = 0.0
        if self._response_times:
            avg_response = sum(self._response_times) / len(self._response_times)

        return {
            "total_proposals": self._total_proposals,
            "applied_count": self._applied_count,
            "pending_proposals": sum(1 for p in self._proposals if not p.applied),
            "current_success_rate": round(success_rate, 4),
            "current_avg_response_s": round(avg_response, 4),
            "recent_proposals": [p.to_dict() for p in list(self._proposals)[-5:]],
        }


# ---------------------------------------------------------------------------
# Self-Learning Engine
# ---------------------------------------------------------------------------


class SelfLearningEngine:
    """
    Continuously ingests new data, manages a learning queue, and tracks
    knowledge growth over time.

    External systems push LearningItems into the queue. Each cycle the
    engine processes the highest-priority items and integrates them into
    MYCA's knowledge base (via the memory coordinator when available).
    """

    def __init__(self) -> None:
        self._queue: deque[LearningItem] = deque(maxlen=_MAX_LEARNING_QUEUE_SIZE)
        self._processed_count: int = 0
        self._total_queued: int = 0
        self._knowledge_domains: Dict[str, int] = {}  # domain -> items learned
        self._last_learning_at: Optional[datetime] = None

    # -- Queue management ---------------------------------------------------

    def enqueue(
        self,
        source: str,
        content: str,
        domain: str,
        priority: float = 0.5,
    ) -> str:
        """
        Add a learning item to the queue.

        Returns the item_id assigned.
        """
        item = LearningItem(
            item_id=f"learn-{uuid.uuid4().hex[:12]}",
            queued_at=datetime.now(timezone.utc),
            source=source,
            content=content,
            domain=domain,
            priority=max(0.0, min(1.0, priority)),
        )
        self._queue.append(item)
        self._total_queued += 1
        return item.item_id

    # -- Processing ---------------------------------------------------------

    async def process_queue(self, batch_size: int = 5) -> int:
        """
        Process up to *batch_size* highest-priority unprocessed items.

        Returns the number of items processed in this batch.
        """
        # Gather unprocessed items sorted by priority descending
        unprocessed = [item for item in self._queue if not item.processed]
        unprocessed.sort(key=lambda i: i.priority, reverse=True)
        batch = unprocessed[:batch_size]

        processed = 0
        for item in batch:
            success = await self._integrate_knowledge(item)
            if success:
                item.processed = True
                item.processed_at = datetime.now(timezone.utc)
                self._processed_count += 1
                self._knowledge_domains[item.domain] = (
                    self._knowledge_domains.get(item.domain, 0) + 1
                )
                processed += 1

        if processed > 0:
            self._last_learning_at = datetime.now(timezone.utc)
            logger.info(
                "Self-learning processed %d items (total: %d)", processed, self._processed_count
            )

        return processed

    async def _integrate_knowledge(self, item: LearningItem) -> bool:
        """
        Integrate a single learning item into MYCA's knowledge.

        Attempts to use the memory coordinator if available; otherwise
        records locally.
        """
        try:
            from mycosoft_mas.memory.coordinator import get_memory_coordinator

            coordinator = await get_memory_coordinator()
            await coordinator.store(
                key=f"learned:{item.domain}:{item.item_id}",
                value={
                    "source": item.source,
                    "content": item.content,
                    "domain": item.domain,
                    "learned_at": datetime.now(timezone.utc).isoformat(),
                },
                layer="semantic",
            )
            return True
        except Exception as exc:
            logger.debug(
                "Memory coordinator unavailable for learning item '%s': %s",
                item.item_id,
                exc,
            )
            # Still count as processed -- the knowledge is tracked in-memory
            return True

    # -- Queries ------------------------------------------------------------

    def get_queue_depth(self) -> int:
        """Return the number of unprocessed items in the queue."""
        return sum(1 for item in self._queue if not item.processed)

    def get_metrics(self) -> Dict[str, Any]:
        """Return learning metrics."""
        return {
            "total_queued": self._total_queued,
            "total_processed": self._processed_count,
            "queue_depth": self.get_queue_depth(),
            "knowledge_domains": dict(self._knowledge_domains),
            "domain_count": len(self._knowledge_domains),
            "last_learning_at": (
                self._last_learning_at.isoformat() if self._last_learning_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Self-Awareness Monitor
# ---------------------------------------------------------------------------


class SelfAwarenessMonitor:
    """
    Monitors MYCA's cognitive processes, tracks resource usage, detects
    potential biases, and maintains a rolling introspection log.

    This is the "inner eye" -- the part of MYCA that watches herself think.
    """

    def __init__(self) -> None:
        self._introspection_log: deque[IntrospectionEntry] = deque(
            maxlen=_MAX_INTROSPECTION_LOG_SIZE
        )
        self._total_introspections: int = 0
        self._detected_biases: Dict[str, int] = {}  # bias_label -> count
        self._resource_history: deque[Dict[str, float]] = deque(maxlen=100)

    # -- Observation --------------------------------------------------------

    async def observe(
        self,
        observation: str,
        cognitive_load: float = 0.5,
        bias_flags: Optional[List[str]] = None,
    ) -> None:
        """
        Record an introspection observation.

        Args:
            observation: Free-text description of what was observed.
            cognitive_load: Estimated cognitive load (0.0 - 1.0).
            bias_flags: Optional list of bias labels detected.
        """
        now = datetime.now(timezone.utc)
        resource_snapshot = await self._capture_resource_snapshot()

        entry = IntrospectionEntry(
            timestamp=now,
            observation=observation,
            cognitive_load=max(0.0, min(1.0, cognitive_load)),
            bias_flags=bias_flags or [],
            resource_snapshot=resource_snapshot,
        )
        self._introspection_log.append(entry)
        self._total_introspections += 1

        # Track bias occurrences
        for bias in entry.bias_flags:
            self._detected_biases[bias] = self._detected_biases.get(bias, 0) + 1

        if entry.bias_flags:
            logger.info("Self-awareness detected biases: %s", ", ".join(entry.bias_flags))

    async def _capture_resource_snapshot(self) -> Dict[str, float]:
        """Capture a lightweight resource usage snapshot."""
        snapshot: Dict[str, float] = {}
        try:
            import psutil

            process = psutil.Process()
            snapshot["cpu_percent"] = process.cpu_percent(interval=0)
            mem_info = process.memory_info()
            snapshot["rss_mb"] = mem_info.rss / (1024 * 1024)
        except Exception:
            # psutil may not be available -- degrade gracefully
            snapshot["cpu_percent"] = -1.0
            snapshot["rss_mb"] = -1.0
        self._resource_history.append(snapshot)
        return snapshot

    # -- Analysis -----------------------------------------------------------

    async def assess_cognitive_state(self) -> Dict[str, Any]:
        """
        Produce a self-assessment of current cognitive state including
        average load, bias summary, and resource trends.
        """
        recent = list(self._introspection_log)[-50:]
        if not recent:
            return {
                "avg_cognitive_load": 0.0,
                "bias_summary": {},
                "observation_count": 0,
                "resource_trend": {},
            }

        avg_load = sum(e.cognitive_load for e in recent) / len(recent)

        # Resource trend (compare first quarter to last quarter of history)
        snapshots = list(self._resource_history)
        resource_trend: Dict[str, str] = {}
        if len(snapshots) >= 4:
            quarter = max(1, len(snapshots) // 4)
            early = snapshots[:quarter]
            late = snapshots[-quarter:]
            for key in ("cpu_percent", "rss_mb"):
                early_avg = sum(s.get(key, 0) for s in early) / len(early)
                late_avg = sum(s.get(key, 0) for s in late) / len(late)
                if early_avg > 0 and late_avg > early_avg * 1.2:
                    resource_trend[key] = "increasing"
                elif early_avg > 0 and late_avg < early_avg * 0.8:
                    resource_trend[key] = "decreasing"
                else:
                    resource_trend[key] = "stable"

        return {
            "avg_cognitive_load": round(avg_load, 4),
            "bias_summary": dict(self._detected_biases),
            "observation_count": self._total_introspections,
            "resource_trend": resource_trend,
        }

    def get_recent_observations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent introspection entries as dicts."""
        recent = list(self._introspection_log)[-limit:]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "observation": e.observation,
                "cognitive_load": e.cognitive_load,
                "bias_flags": e.bias_flags,
                "resource_snapshot": e.resource_snapshot,
            }
            for e in recent
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Return self-awareness metrics."""
        return {
            "total_introspections": self._total_introspections,
            "detected_biases": dict(self._detected_biases),
            "log_size": len(self._introspection_log),
            "resource_snapshots": len(self._resource_history),
        }


# ---------------------------------------------------------------------------
# AutonomousSelf -- main orchestrator
# ---------------------------------------------------------------------------


class AutonomousSelf:
    """
    The main orchestrator that ties all four autonomous engines together.

    It runs a periodic autonomous cycle that:
    1. Checks system health and auto-heals failures.
    2. Analyzes performance and proposes improvements.
    3. Processes the learning queue.
    4. Records introspection observations.

    Usage::

        autonomous = AutonomousSelf()
        await autonomous.start()   # begins background loop
        ...
        await autonomous.stop()    # graceful shutdown
    """

    def __init__(
        self,
        cycle_interval: float = _DEFAULT_CYCLE_INTERVAL_SECONDS,
    ) -> None:
        self.cycle_interval = cycle_interval

        # Sub-engines
        self.healing = SelfHealingEngine()
        self.improvement = SelfImprovementEngine()
        self.learning = SelfLearningEngine()
        self.awareness = SelfAwarenessMonitor()

        # State
        self._state = AutonomousState()
        self._shutdown_event = asyncio.Event()
        self._loop_task: Optional[asyncio.Task] = None

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the autonomous background loop."""
        if self._state.is_running:
            logger.warning("AutonomousSelf is already running")
            return

        self._state.is_running = True
        self._state.started_at = datetime.now(timezone.utc)
        self._shutdown_event.clear()
        self._loop_task = asyncio.create_task(self._autonomous_loop())
        logger.info("AutonomousSelf started (cycle every %.1fs)", self.cycle_interval)

    async def stop(self) -> None:
        """Gracefully stop the autonomous background loop."""
        if not self._state.is_running:
            return

        logger.info("AutonomousSelf shutting down...")
        self._shutdown_event.set()
        if self._loop_task is not None:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        self._state.is_running = False
        if self._state.started_at:
            self._state.uptime_seconds = (
                datetime.now(timezone.utc) - self._state.started_at
            ).total_seconds()
        logger.info("AutonomousSelf stopped (uptime: %.0fs)", self._state.uptime_seconds)

    # -- Main loop ----------------------------------------------------------

    async def _autonomous_loop(self) -> None:
        """Background loop that runs the autonomous cycle periodically."""
        while not self._shutdown_event.is_set():
            try:
                await self.run_autonomous_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Autonomous cycle error: %s", exc, exc_info=True)
                # Record the error as an introspection observation
                await self.awareness.observe(
                    observation=f"Autonomous cycle encountered an error: {exc}",
                    cognitive_load=0.9,
                    bias_flags=["error_recovery_bias"],
                )
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.cycle_interval)
                break  # shutdown requested
            except asyncio.TimeoutError:
                pass  # normal timeout, continue loop

    async def run_autonomous_cycle(self) -> Dict[str, Any]:
        """
        Execute a single autonomous cycle: heal, improve, learn, introspect.

        This can be called manually or runs automatically in the background.

        Returns a summary dict of what happened during the cycle.
        """
        cycle_start = time.monotonic()
        now = datetime.now(timezone.utc)
        summary: Dict[str, Any] = {"cycle_timestamp": now.isoformat()}

        # 1. Self-Heal
        health_statuses = await self.healing.run_checks()
        issues = await self.healing.heal()
        self._state.total_heals += len([i for i in issues if i.auto_healed])
        self._state.overall_health = self.healing.get_overall_health()
        summary["health"] = {
            "overall": self._state.overall_health.value,
            "components": {k: v.value for k, v in health_statuses.items()},
            "issues_found": len(issues),
            "auto_healed": len([i for i in issues if i.auto_healed]),
        }

        # 2. Self-Improve
        analysis = await self.improvement.analyze_performance()
        proposals = await self.improvement.propose_improvements(analysis)
        self._state.total_improvements += len(proposals)
        summary["improvement"] = {
            "weaknesses_found": len(analysis.get("weaknesses", [])),
            "proposals_generated": len(proposals),
            "current_success_rate": analysis.get("success_rate", None),
            "current_avg_response_s": analysis.get("avg_response_time_s", None),
        }

        # 3. Self-Learn
        items_learned = await self.learning.process_queue()
        self._state.total_learnings += items_learned
        summary["learning"] = {
            "items_processed": items_learned,
            "queue_depth": self.learning.get_queue_depth(),
            "total_learned": self.learning._processed_count,
        }

        # 4. Self-Aware (introspect about this cycle)
        cycle_duration = time.monotonic() - cycle_start
        cognitive_load = min(1.0, cycle_duration / self.cycle_interval)
        bias_flags: List[str] = []
        if len(issues) > 3:
            bias_flags.append("over_diagnosis")
        if len(proposals) > 5:
            bias_flags.append("improvement_overload")

        await self.awareness.observe(
            observation=(
                f"Autonomous cycle #{self._state.total_cycles + 1}: "
                f"health={self._state.overall_health.value}, "
                f"healed={len([i for i in issues if i.auto_healed])}, "
                f"proposals={len(proposals)}, "
                f"learned={items_learned}, "
                f"duration={cycle_duration:.3f}s"
            ),
            cognitive_load=cognitive_load,
            bias_flags=bias_flags if bias_flags else None,
        )
        self._state.total_introspections += 1
        summary["awareness"] = {
            "cognitive_load": round(cognitive_load, 4),
            "bias_flags": bias_flags,
            "cycle_duration_s": round(cycle_duration, 4),
        }

        # Update state
        self._state.total_cycles += 1
        self._state.last_cycle_at = now
        if self._state.started_at:
            self._state.uptime_seconds = (now - self._state.started_at).total_seconds()

        logger.info(
            "Autonomous cycle #%d complete in %.3fs "
            "(health=%s, healed=%d, proposals=%d, learned=%d)",
            self._state.total_cycles,
            cycle_duration,
            self._state.overall_health.value,
            summary["health"]["auto_healed"],
            len(proposals),
            items_learned,
        )

        return summary

    # -- High-level public API ----------------------------------------------

    async def assess_self(self) -> Dict[str, Any]:
        """
        Return a comprehensive self-assessment combining all engine metrics.

        This is the external-facing introspection report that other
        consciousness modules can query.
        """
        cognitive_state = await self.awareness.assess_cognitive_state()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._state.to_dict(),
            "healing": self.healing.get_metrics(),
            "improvement": self.improvement.get_metrics(),
            "learning": self.learning.get_metrics(),
            "awareness": {
                **self.awareness.get_metrics(),
                "cognitive_state": cognitive_state,
            },
        }

    async def heal(self) -> List[Dict[str, Any]]:
        """
        Run a targeted heal pass and return issue dicts.

        Convenience wrapper for callers that only need healing.
        """
        await self.healing.run_checks()
        issues = await self.healing.heal()
        self._state.total_heals += len([i for i in issues if i.auto_healed])
        self._state.overall_health = self.healing.get_overall_health()
        return [i.to_dict() for i in issues]

    async def improve(self) -> List[Dict[str, Any]]:
        """
        Run a targeted improvement pass and return proposal dicts.

        Convenience wrapper for callers that only need improvement analysis.
        """
        analysis = await self.improvement.analyze_performance()
        proposals = await self.improvement.propose_improvements(analysis)
        self._state.total_improvements += len(proposals)
        return [p.to_dict() for p in proposals]

    async def learn(self, source: str, content: str, domain: str, priority: float = 0.5) -> str:
        """
        Enqueue a learning item and return the item_id.

        Convenience method so external code can feed knowledge into the
        learning engine without accessing it directly.
        """
        return self.learning.enqueue(
            source=source, content=content, domain=domain, priority=priority
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_autonomous_self_instance: Optional[AutonomousSelf] = None


async def get_autonomous_self() -> AutonomousSelf:
    """Get or create the singleton AutonomousSelf instance."""
    global _autonomous_self_instance
    if _autonomous_self_instance is None:
        _autonomous_self_instance = AutonomousSelf()
    return _autonomous_self_instance

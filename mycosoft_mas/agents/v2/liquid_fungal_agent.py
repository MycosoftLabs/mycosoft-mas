"""
Liquid Fungal Integration Agent — Orchestrating Bio-Digital Hybrid Intelligence

Ties together:
  - LiquidTemporalProcessor: adaptive temporal processing of FCI biosignals
  - FungalMemoryBridge: biological ↔ digital memory bridging
  - RecursiveSelfImprovementEngine: formal improvement cycles with benchmarks

Capabilities:
  - process_biosignal: Process FCI data through liquid temporal processor
  - bridge_memory: Create/query biological bookmarks
  - run_improvement_cycle: Execute one recursive self-improvement cycle
  - benchmark: Run and record performance benchmarks
  - get_adaptation_status: Return current adaptation metrics

This agent is the primary interface for Liquid AI-inspired fungal integration,
enabling efficient edge inference, bio-inspired memory, and recursive
self-improvement across the Mycosoft MAS.

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from __future__ import annotations

import logging
from typing import Any, Dict

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


class LiquidFungalIntegrationAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """
    Orchestrates Liquid AI-inspired fungal integration.

    Bridges liquid-inspired temporal models with fungal computing substrate
    for adaptive biosignal processing, biological memory bridging, and
    recursive self-improvement.
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = [
            "process_biosignal",
            "bridge_memory",
            "run_improvement_cycle",
            "benchmark",
            "get_adaptation_status",
        ]
        self._processor = None
        self._memory_bridge = None
        self._improvement_engine = None

    def _ensure_processor(self):
        """Lazy-init the LiquidTemporalProcessor."""
        if self._processor is None:
            try:
                from mycosoft_mas.engines.liquid_temporal import (
                    LiquidTemporalProcessor,
                )

                self._processor = LiquidTemporalProcessor(config=self.config.get("processor", {}))
            except Exception as exc:
                logger.warning("Failed to init LiquidTemporalProcessor: %s", exc)

    def _ensure_memory_bridge(self):
        """Lazy-init the FungalMemoryBridge."""
        if self._memory_bridge is None:
            try:
                from mycosoft_mas.memory.fungal_memory_bridge import (
                    FungalMemoryBridge,
                )

                self._memory_bridge = FungalMemoryBridge()
            except Exception as exc:
                logger.warning("Failed to init FungalMemoryBridge: %s", exc)

    def _ensure_improvement_engine(self):
        """Lazy-init the RecursiveSelfImprovementEngine."""
        if self._improvement_engine is None:
            try:
                from mycosoft_mas.engines.recursive_improvement import (
                    RecursiveSelfImprovementEngine,
                )

                # Try to connect to existing services
                learning_feedback = None
                self_reflection = None
                continuous_learner = None

                try:
                    from mycosoft_mas.services.learning_feedback import (
                        get_learning_service,
                    )

                    learning_feedback = get_learning_service()
                except Exception:
                    pass

                self._improvement_engine = RecursiveSelfImprovementEngine(
                    learning_feedback=learning_feedback,
                    self_reflection=self_reflection,
                    continuous_learner=continuous_learner,
                )
            except Exception as exc:
                logger.warning("Failed to init RecursiveSelfImprovementEngine: %s", exc)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "process_biosignal": self._process_biosignal,
            "bridge_memory": self._bridge_memory,
            "run_improvement_cycle": self._run_improvement_cycle,
            "benchmark": self._benchmark,
            "get_adaptation_status": self._get_adaptation_status,
        }
        handler = handlers.get(task_type)
        if handler:
            return await handler(task)
        return {
            "status": "skipped",
            "result": {"reason": f"unknown task type: {task_type}"},
        }

    # ===== Task Handlers ==================================================

    async def _process_biosignal(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process FCI biosignal through liquid temporal processor."""
        try:
            self._ensure_processor()
            if not self._processor:
                return {"status": "error", "result": {"error": "Processor unavailable"}}

            channel_id = task.get("channel_id", "ch0")
            samples = task.get("samples", [])
            timestamps = task.get("timestamps")

            if not samples:
                return {"status": "error", "result": {"error": "No samples provided"}}

            result = self._processor.process_continuous(
                channel_id=channel_id,
                samples=samples,
                timestamps=timestamps,
            )

            # Auto-create bookmark on state transitions
            transition = self._processor.detect_state_transition(channel_id)
            bookmark_created = False
            if transition and transition.confidence >= 0.6:
                self._ensure_memory_bridge()
                if self._memory_bridge:
                    await self._memory_bridge.create_biological_bookmark(
                        channel_id=channel_id,
                        from_state=transition.from_state,
                        to_state=transition.to_state,
                        significance=transition.confidence,
                        fungal_state_snapshot=result.signal_dynamics,
                    )
                    bookmark_created = True

            return {
                "status": "success",
                "result": {
                    "processed_stream": result.to_dict(),
                    "transition": transition.to_dict() if transition else None,
                    "bookmark_created": bookmark_created,
                },
            }
        except Exception as exc:
            logger.warning("process_biosignal failed: %s", exc)
            return {"status": "error", "result": {"error": str(exc)}}

    async def _bridge_memory(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create or query biological bookmarks."""
        try:
            self._ensure_memory_bridge()
            if not self._memory_bridge:
                return {"status": "error", "result": {"error": "Memory bridge unavailable"}}

            action = task.get("action", "query")

            if action == "create":
                bookmark = await self._memory_bridge.create_biological_bookmark(
                    channel_id=task.get("channel_id", "ch0"),
                    from_state=task.get("from_state", "unknown"),
                    to_state=task.get("to_state", "unknown"),
                    significance=task.get("significance", 0.5),
                    fungal_state_snapshot=task.get("fungal_state_snapshot", {}),
                    metadata=task.get("metadata", {}),
                )
                return {"status": "success", "result": {"bookmark": bookmark.to_dict()}}

            elif action == "query":
                bookmarks = self._memory_bridge.query_biological_memory(
                    channel_id=task.get("channel_id"),
                    min_significance=task.get("min_significance", 0.0),
                )
                return {
                    "status": "success",
                    "result": {
                        "bookmarks": [b.to_dict() for b in bookmarks[:20]],
                        "total": len(bookmarks),
                    },
                }

            elif action == "hysteresis":
                report = self._memory_bridge.get_hysteresis_report()
                return {"status": "success", "result": report}

            elif action == "consolidate":
                count = await self._memory_bridge.consolidate_to_semantic()
                return {
                    "status": "success",
                    "result": {"patterns_consolidated": count},
                }

            elif action == "track_memristive":
                state = self._memory_bridge.track_memristive_state(
                    channel_id=task.get("channel_id", "ch0"),
                    stimulus=task.get("stimulus", 0.0),
                    response=task.get("response", 0.0),
                )
                return {"status": "success", "result": state.to_dict()}

            return {
                "status": "error",
                "result": {"error": f"Unknown action: {action}"},
            }
        except Exception as exc:
            logger.warning("bridge_memory failed: %s", exc)
            return {"status": "error", "result": {"error": str(exc)}}

    async def _run_improvement_cycle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one recursive self-improvement cycle."""
        try:
            self._ensure_improvement_engine()
            if not self._improvement_engine:
                return {
                    "status": "error",
                    "result": {"error": "Improvement engine unavailable"},
                }

            result = self._improvement_engine.run_cycle()
            return {"status": "success", "result": result.to_dict()}
        except Exception as exc:
            logger.warning("run_improvement_cycle failed: %s", exc)
            return {"status": "error", "result": {"error": str(exc)}}

    async def _benchmark(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run and record performance benchmarks."""
        try:
            self._ensure_improvement_engine()
            if not self._improvement_engine:
                return {
                    "status": "error",
                    "result": {"error": "Improvement engine unavailable"},
                }

            action = task.get("action", "summary")

            if action == "summary":
                return {
                    "status": "success",
                    "result": self._improvement_engine.get_summary(),
                }
            elif action == "history":
                return {
                    "status": "success",
                    "result": {"benchmarks": self._improvement_engine.get_benchmarks()},
                }
            elif action == "hypotheses":
                status_filter = task.get("status_filter")
                return {
                    "status": "success",
                    "result": {
                        "hypotheses": self._improvement_engine.get_hypotheses(status=status_filter)
                    },
                }

            return {
                "status": "error",
                "result": {"error": f"Unknown action: {action}"},
            }
        except Exception as exc:
            logger.warning("benchmark failed: %s", exc)
            return {"status": "error", "result": {"error": str(exc)}}

    async def _get_adaptation_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return current adaptation metrics across all subsystems."""
        try:
            status: Dict[str, Any] = {"agent_id": self.agent_id}

            # Processor metrics
            self._ensure_processor()
            if self._processor:
                status["temporal_processor"] = self._processor.get_adaptation_metrics()

            # Memory bridge metrics
            self._ensure_memory_bridge()
            if self._memory_bridge:
                status["memory_bridge"] = self._memory_bridge.get_summary()
                status["hysteresis"] = self._memory_bridge.get_hysteresis_report()

            # Improvement engine metrics
            self._ensure_improvement_engine()
            if self._improvement_engine:
                status["improvement_engine"] = self._improvement_engine.get_summary()

            return {"status": "success", "result": status}
        except Exception as exc:
            logger.warning("get_adaptation_status failed: %s", exc)
            return {"status": "error", "result": {"error": str(exc)}}

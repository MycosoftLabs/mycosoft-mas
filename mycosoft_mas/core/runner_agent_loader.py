"""
Runner Agent Loader

Loads core registry agents into the 24/7 agent runner.

Native agent cycles are hard-timeout wrapped so sync I/O (subprocess, DB)
cannot stall the uvicorn event loop on :8001.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from mycosoft_mas.core.agent_registry import AgentDefinition, get_agent_registry
from mycosoft_mas.core.agent_runner import get_agent_runner

logger = logging.getLogger(__name__)

NATIVE_CYCLE_TIMEOUT_SEC = float(os.getenv("AGENT_NATIVE_CYCLE_TIMEOUT_SEC", "10"))


@dataclass
class RunnerLoadResult:
    total_requested: int
    native_loaded: int
    fallback_loaded: int
    failed: int


class LoadedRunnerAgent:
    """Adapter the runner can execute every cycle."""

    def __init__(
        self,
        definition: AgentDefinition,
        delegate: Optional[Any] = None,
        mode: str = "fallback",
        error: Optional[str] = None,
    ):
        self.definition = definition
        self.delegate = delegate
        self.mode = mode
        self.error = error
        self.agent_id = definition.agent_id
        self.name = definition.display_name
        self._cycle_count = 0

    async def run_cycle(self) -> Dict[str, Any]:
        self._cycle_count += 1
        cycle_time = datetime.utcnow().isoformat() + "Z"

        if self.delegate is not None and self.mode == "native":
            try:
                return await asyncio.wait_for(
                    self._run_native(cycle_time),
                    timeout=NATIVE_CYCLE_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Native cycle timeout for %s after %ss — falling back to presence",
                    self.agent_id,
                    NATIVE_CYCLE_TIMEOUT_SEC,
                )
                self.mode = "fallback"
                self.error = f"native_timeout_{NATIVE_CYCLE_TIMEOUT_SEC}s"
                # Drop delegate so subsequent cycles stay light.
                self.delegate = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Native cycle error for %s: %s", self.agent_id, exc)
                self.error = str(exc)[:300]

        return self._presence_result()

    async def _run_native(self, cycle_time: str) -> Dict[str, Any]:
        assert self.delegate is not None
        if hasattr(self.delegate, "run_cycle"):
            result = await self.delegate.run_cycle()
            if isinstance(result, dict):
                return result
            return {
                "tasks_processed": 1,
                "insights_generated": 0,
                "knowledge_added": 0,
                "summary": f"{self.definition.display_name} native run_cycle completed",
            }
        if hasattr(self.delegate, "process_task"):
            # Do not await heavy memory writes on the request loop path;
            # process_task may still call record_task_completion — that path
            # now has its own timeout in memory_mixin.
            await self.delegate.process_task(
                {
                    "type": "continuous_cycle",
                    "timestamp": cycle_time,
                    "source": "agent_runner",
                    "action": "process",
                }
            )
            return {
                "tasks_processed": 1,
                "insights_generated": 0,
                "knowledge_added": 0,
                "summary": f"{self.definition.display_name} processed cycle task",
            }
        return self._presence_result()

    def _presence_result(self) -> Dict[str, Any]:
        summary = (
            f"{self.definition.display_name} online in {self.mode} mode "
            f"(cycle {self._cycle_count})"
        )
        if self.error:
            summary += f"; reason: {self.error}"
        # Intentionally no heartbeat/redis/DB imports here — those have wedged :8001.
        return {
            "tasks_processed": 0,
            "insights_generated": 0,
            "knowledge_added": 0,
            "summary": summary,
        }


def _build_agent_config(definition: AgentDefinition) -> Dict[str, Any]:
    return {
        "agent_id": definition.agent_id,
        "display_name": definition.display_name,
        "category": definition.category.value,
        "capabilities": [c.value for c in definition.capabilities],
        "runner_managed": True,
    }


def _instantiate_native_agent(definition: AgentDefinition) -> Any:
    module = importlib.import_module(definition.module_path)
    cls = getattr(module, definition.class_name)

    config = _build_agent_config(definition)
    attempts = (
        lambda: cls(agent_id=definition.agent_id, name=definition.display_name, config=config),
        lambda: cls(definition.agent_id, definition.display_name, config),
        lambda: cls(),
    )
    for attempt in attempts:
        try:
            return attempt()
        except Exception:  # noqa: BLE001
            pass

    signature = inspect.signature(cls.__init__)
    kwargs: Dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if name == "agent_id":
            kwargs[name] = definition.agent_id
        elif name == "name":
            kwargs[name] = definition.display_name
        elif name == "config":
            kwargs[name] = config
        elif param.default is inspect._empty:
            raise TypeError(f"Required ctor arg '{name}' not supported")
    return cls(**kwargs)


def load_core_runner_agents() -> tuple[list[LoadedRunnerAgent], RunnerLoadResult]:
    """
    Load active registry agents.

    Default is light presence (delegate=None) to keep :8001 responsive.
    Set AGENT_RUNNER_NATIVE_CORE=1 to attempt native instantiation (risky).
    """
    registry = get_agent_registry()
    active_definitions = registry.list_active()
    agents: list[LoadedRunnerAgent] = []
    native_loaded = 0
    fallback_loaded = 0
    failed = 0
    allow_native = os.getenv("AGENT_RUNNER_NATIVE_CORE", "0") == "1"

    for definition in active_definitions:
        if not allow_native:
            agents.append(
                LoadedRunnerAgent(
                    definition=definition,
                    delegate=None,
                    mode="fallback",
                    error="light_presence_core",
                )
            )
            fallback_loaded += 1
            continue
        try:
            delegate = _instantiate_native_agent(definition)
            agents.append(
                LoadedRunnerAgent(definition=definition, delegate=delegate, mode="native")
            )
            native_loaded += 1
        except Exception as exc:  # noqa: BLE001
            agents.append(
                LoadedRunnerAgent(
                    definition=definition,
                    delegate=None,
                    mode="fallback",
                    error=str(exc),
                )
            )
            fallback_loaded += 1

    return (
        agents,
        RunnerLoadResult(
            total_requested=len(active_definitions),
            native_loaded=native_loaded,
            fallback_loaded=fallback_loaded,
            failed=failed,
        ),
    )


async def restart_runner_with_core_agents() -> Dict[str, Any]:
    runner = get_agent_runner()
    if runner.running:
        await runner.stop()
        await asyncio.sleep(0.1)

    agents, load_result = await asyncio.to_thread(load_core_runner_agents)
    # Longer interval for full-registry presence to reduce chatter.
    runner.configure(cycle_interval=float(os.getenv("AGENT_CORE_CYCLE_INTERVAL_SEC", "300")))
    await runner.start(agents)
    status = await runner.get_status()
    return {
        "status": "started",
        "message": "24/7 agent runner started with core registry agents",
        "load": {
            "total_requested": load_result.total_requested,
            "native_loaded": load_result.native_loaded,
            "fallback_loaded": load_result.fallback_loaded,
            "failed": load_result.failed,
        },
        "runner": {
            "running": status.get("running"),
            "agents": status.get("agents"),
            "cycle_interval": status.get("cycle_interval"),
        },
    }

"""
Critical always-on watchers for MAS 24/7 runner.

Loads only NLM/security/login-related agents so MAS_SKIP_BACKGROUND_STARTUP
can stay on (full background startup wedges :8001 via collectors).

IMPORTANT: Never instantiate native agent classes here. Constructors (ImmuneSystem,
WorkspaceSecurity) create asyncio queues / import scanners / can run sync subprocess
work. Light presence cycles keep watchers "online" without blocking uvicorn.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from mycosoft_mas.core.agent_registry import AgentCategory, AgentDefinition, get_agent_registry
from mycosoft_mas.core.agent_runner import get_agent_runner
from mycosoft_mas.core.runner_agent_loader import LoadedRunnerAgent

# Keep this list small — avoid OOM / event-loop stalls.
CRITICAL_REGISTRY_IDS = (
    "guardian-agent",
    "immune_system",
)

# Agents that exist in code but may not be in the voice registry catalog (~47 entries).
EXTRA_CRITICAL: Tuple[Tuple[str, str, str, str], ...] = (
    (
        "workspace_security",
        "WorkspaceSecurityAgent",
        "mycosoft_mas.agents.workspace_security_agent",
        "WorkspaceSecurityAgent",
    ),
    (
        "nlm-agent",
        "NLMAgent",
        "mycosoft_mas.agents.v2.data_agents",
        "NLMAgent",
    ),
    (
        "security-monitor-agent",
        "SecurityMonitorAgentV2",
        "mycosoft_mas.agents.v2.security_agents",
        "SecurityMonitorAgentV2",
    ),
)


@dataclass
class CriticalLoadResult:
    requested: List[str]
    loaded: List[Dict[str, str]]
    failed: List[Dict[str, str]]


def _extra_definition(agent_id: str, display: str, module: str, class_name: str) -> AgentDefinition:
    try:
        from mycosoft_mas.core.agent_registry import AgentCapability

        return AgentDefinition(
            agent_id=agent_id,
            name=class_name,
            display_name=display,
            description=f"Critical always-on watcher: {display}",
            category=(
                AgentCategory.DATA
                if agent_id.startswith("nlm")
                else AgentCategory.SECURITY
            ),
            capabilities=[AgentCapability.ANALYZE],
            module_path=module,
            class_name=class_name,
            keywords=["critical", "watcher"],
            voice_triggers=[],
            is_active=True,
        )
    except Exception:
        class _Def:
            pass

        d = _Def()
        d.agent_id = agent_id
        d.name = class_name
        d.display_name = display
        d.description = display
        d.category = AgentCategory.SECURITY
        d.capabilities = []
        d.module_path = module
        d.class_name = class_name
        d.keywords = []
        d.voice_triggers = []
        d.is_active = True
        return d  # type: ignore[return-value]


def _light_agent(definition: AgentDefinition) -> LoadedRunnerAgent:
    """Presence-only adapter — no native delegate, no imports of agent modules."""
    return LoadedRunnerAgent(
        definition=definition,
        delegate=None,
        mode="fallback",
        error="light_presence_cycle",
    )


def load_critical_runner_agents() -> Tuple[List[LoadedRunnerAgent], CriticalLoadResult]:
    registry = get_agent_registry()
    agents: List[LoadedRunnerAgent] = []
    loaded: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []
    requested: List[str] = []

    for agent_id in CRITICAL_REGISTRY_IDS:
        requested.append(agent_id)
        definition = registry.get(agent_id)
        if not definition:
            # Still register a synthetic definition so the watcher appears online.
            definition = _extra_definition(
                agent_id,
                agent_id,
                "mycosoft_mas.agents.base_agent",
                "BaseAgent",
            )
            failed.append({"agent_id": agent_id, "error": "not_in_registry_using_synthetic"})
        agent = _light_agent(definition)
        agents.append(agent)
        loaded.append({"agent_id": agent_id, "mode": agent.mode, "error": agent.error or ""})

    for agent_id, display, module, class_name in EXTRA_CRITICAL:
        requested.append(agent_id)
        definition = _extra_definition(agent_id, display, module, class_name)
        agent = _light_agent(definition)
        agents.append(agent)
        loaded.append({"agent_id": agent_id, "mode": agent.mode, "error": agent.error or ""})

    return agents, CriticalLoadResult(requested=requested, loaded=loaded, failed=failed)


async def restart_runner_with_critical_agents() -> Dict[str, Any]:
    runner = get_agent_runner()
    if runner.running:
        await runner.stop()
        await asyncio.sleep(0.05)

    # Pure definition work — no agent class imports; safe on event loop or thread.
    agents, result = await asyncio.to_thread(load_critical_runner_agents)

    # Critical watchers: shorter interval, hard timeout already in AgentCycleRunner.
    interval = float(os.getenv("AGENT_CRITICAL_CYCLE_INTERVAL_SEC", "60"))
    timeout = float(os.getenv("AGENT_CRITICAL_CYCLE_TIMEOUT_SEC", "10"))
    runner.configure(cycle_interval=interval, cycle_timeout=timeout)
    await runner.start(agents)

    supervisor_error = None
    try:
        from mycosoft_mas.core.agent_supervisor import get_supervisor

        supervisor = get_supervisor()
        if not getattr(supervisor, "_running", False):
            await supervisor.start()
    except Exception as exc:  # noqa: BLE001
        supervisor_error = str(exc)

    status = await runner.get_status()
    return {
        "status": "started",
        "message": "24/7 runner started with critical NLM/security/login watchers only",
        "requested": result.requested,
        "loaded": result.loaded,
        "failed": result.failed,
        "supervisor_error": supervisor_error,
        "runner": {
            "running": status.get("running"),
            "agents": status.get("agents"),
            "agent_ids": status.get("agent_ids"),
            "cycle_interval": status.get("cycle_interval"),
            "cycle_timeout": status.get("cycle_timeout"),
        },
    }

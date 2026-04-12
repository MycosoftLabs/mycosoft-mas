"""
Domain-level integration hooks to fan key MAS events into Deep Agents.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from mycosoft_mas.deep_agents.config import get_deep_agents_config
from mycosoft_mas.deep_agents.orchestrator import get_deep_agent_orchestrator

logger = logging.getLogger(__name__)

_DOMAIN_DEFAULT_AGENT = {
    "search": "myca-research",
    "security": "security-agent",
    "device": "ops-agent",
    "natureos": "ops-agent",
    "myca": "myca-secretary",
}


def _hooks_enabled() -> bool:
    raw = os.getenv("MYCA_DEEP_AGENTS_DOMAIN_HOOKS_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def submit_domain_task(
    *,
    domain: str,
    task: str,
    context: Dict[str, Any] | None = None,
    preferred_agent: str | None = None,
) -> None:
    if not _hooks_enabled():
        return

    cfg = get_deep_agents_config()
    if not cfg.enabled and not cfg.protocol_enabled:
        return

    agent_name = preferred_agent or _DOMAIN_DEFAULT_AGENT.get(domain, "myca-secretary")
    orchestrator = get_deep_agent_orchestrator()
    await orchestrator.submit_task(
        agent_name=agent_name,
        task=task,
        context={
            "domain": domain,
            **(context or {}),
        },
    )


def schedule_domain_task(
    *,
    domain: str,
    task: str,
    context: Dict[str, Any] | None = None,
    preferred_agent: str | None = None,
) -> None:
    try:
        asyncio.create_task(
            submit_domain_task(
                domain=domain,
                task=task,
                context=context,
                preferred_agent=preferred_agent,
            )
        )
    except RuntimeError:
        logger.debug("No running event loop; skipped domain hook for %s", domain)

"""
Deep Agents integration surface for MAS.

This package provides a feature-flagged wrapper around LangChain Deep Agents
so MAS can roll out async subagent orchestration without breaking existing
runtime behavior.
"""

from .config import get_deep_agents_config
from .domain_hooks import schedule_domain_task
from .orchestrator import DeepAgentOrchestrator, get_deep_agent_orchestrator

__all__ = [
    "DeepAgentOrchestrator",
    "get_deep_agent_orchestrator",
    "get_deep_agents_config",
    "schedule_domain_task",
]

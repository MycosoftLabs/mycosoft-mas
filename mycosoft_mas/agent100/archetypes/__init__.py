"""Archetype registry — maps archetype id to harness class."""

from __future__ import annotations

from mycosoft_mas.agent100.archetypes.handlers import DefaultAgent100, archetype_handler_for
from mycosoft_mas.agent100.types import AgentRow


def build_agent(row: AgentRow):
    cls = archetype_handler_for(row.archetype)
    return cls(row)


__all__ = ["build_agent", "DefaultAgent100", "archetype_handler_for"]

"""Business agents: grants, SBIR/STTR, project management."""

try:
    from mycosoft_mas.agents.business.grant_agent import GrantAgent
except ImportError:
    GrantAgent = None  # type: ignore[misc, assignment]

__all__ = ["GrantAgent"]

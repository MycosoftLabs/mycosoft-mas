"""
Mycosoft MAS Personas Module

Contains MYCA brain persona and sub-agent definitions.
"""

from .sub_agents import (
    SubAgentPersona,
    UserTier,
    get_persona_prompt,
    get_sub_agent,
    get_sub_agent_for_tier,
    get_sub_agent_router,
    list_sub_agents,
)

__all__ = [
    "UserTier",
    "SubAgentPersona",
    "get_sub_agent",
    "get_sub_agent_for_tier",
    "list_sub_agents",
    "get_persona_prompt",
    "get_sub_agent_router",
]

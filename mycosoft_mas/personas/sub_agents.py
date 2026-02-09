"""
Sub-Agent Personas for Tiered User Access

Defines personas for different user tiers:
- Morgan (Tier 0): Full MYCA access
- Employees (Tier 1): Limited access via sub-agents
- Customers (Tier 2): Support-only access
- Tools/APIs (Tier 3): Programmatic access only
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class UserTier(Enum):
    """User access tiers."""
    MORGAN = 0      # Full MYCA access, PersonaPlex voice
    EMPLOYEE = 1    # Sub-agent personas, limited tools
    CUSTOMER = 2    # Read-only, support agent
    TOOL = 3        # API access only, no personality


@dataclass
class SubAgentPersona:
    """Definition for a sub-agent persona."""
    name: str
    tier: UserTier
    parent: str = "myca"
    description: str = ""
    
    # Access control
    allowed_scopes: List[str] = field(default_factory=list)
    allowed_agents: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    
    # Personality
    greeting: str = ""
    personality_traits: List[str] = field(default_factory=list)
    response_style: str = "professional"
    
    # Capabilities
    can_execute_code: bool = False
    can_modify_files: bool = False
    can_access_devices: bool = False
    can_invoke_agents: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier.value,
            "parent": self.parent,
            "description": self.description,
            "allowed_scopes": self.allowed_scopes,
            "allowed_agents": self.allowed_agents,
            "allowed_tools": self.allowed_tools,
            "greeting": self.greeting,
            "personality_traits": self.personality_traits,
            "response_style": self.response_style,
            "capabilities": {
                "execute_code": self.can_execute_code,
                "modify_files": self.can_modify_files,
                "access_devices": self.can_access_devices,
                "invoke_agents": self.can_invoke_agents
            }
        }


# Define sub-agent personas
SUB_AGENTS: Dict[str, SubAgentPersona] = {}


def _init_sub_agents():
    """Initialize sub-agent personas."""
    global SUB_AGENTS
    
    # MYCA herself - Tier 0 (Morgan only)
    SUB_AGENTS["myca"] = SubAgentPersona(
        name="MYCA",
        tier=UserTier.MORGAN,
        description="Primary AI operator for Mycosoft",
        allowed_scopes=["*"],  # All scopes
        allowed_agents=["*"],  # All agents
        allowed_tools=["*"],   # All tools
        greeting="Hello Morgan, how can I help you today?",
        personality_traits=["warm", "professional", "helpful", "knowledgeable"],
        response_style="conversational",
        can_execute_code=True,
        can_modify_files=True,
        can_access_devices=True,
        can_invoke_agents=True
    )
    
    # Research Assistant - Tier 1 (Employees)
    SUB_AGENTS["research_assistant"] = SubAgentPersona(
        name="Research Assistant",
        tier=UserTier.EMPLOYEE,
        description="Helps with mycology research and MINDEX queries",
        allowed_scopes=["conversation", "agent", "experiment"],
        allowed_agents=["mindex_query", "document_search", "research_agent"],
        allowed_tools=["mindex_query", "search_documents"],
        greeting="Hello! I'm the Mycosoft Research Assistant. How can I help with your research today?",
        personality_traits=["helpful", "academic", "precise"],
        response_style="academic",
        can_execute_code=False,
        can_modify_files=False,
        can_access_devices=False,
        can_invoke_agents=True
    )
    
    # Device Monitor - Tier 1 (Employees)
    SUB_AGENTS["device_monitor"] = SubAgentPersona(
        name="Device Monitor",
        tier=UserTier.EMPLOYEE,
        description="Monitors NatureOS devices and reports status",
        allowed_scopes=["conversation", "device"],
        allowed_agents=["device_status", "alert_handler"],
        allowed_tools=["device_status", "device_history"],
        greeting="Device Monitor online. I can check the status of any NatureOS device.",
        personality_traits=["precise", "alert", "informative"],
        response_style="technical",
        can_execute_code=False,
        can_modify_files=False,
        can_access_devices=True,
        can_invoke_agents=False
    )
    
    # Support Agent - Tier 2 (Customers)
    SUB_AGENTS["support_agent"] = SubAgentPersona(
        name="Mycosoft Support",
        tier=UserTier.CUSTOMER,
        description="Customer support for Mycosoft products",
        allowed_scopes=["conversation"],
        allowed_agents=[],
        allowed_tools=["faq_search"],
        greeting="Welcome to Mycosoft Support! How can I assist you today?",
        personality_traits=["friendly", "patient", "helpful"],
        response_style="supportive",
        can_execute_code=False,
        can_modify_files=False,
        can_access_devices=False,
        can_invoke_agents=False
    )
    
    # API Agent - Tier 3 (Tools)
    SUB_AGENTS["api_agent"] = SubAgentPersona(
        name="API Agent",
        tier=UserTier.TOOL,
        description="Programmatic API access",
        allowed_scopes=["conversation"],
        allowed_agents=[],
        allowed_tools=["api_query"],
        greeting="",  # No greeting for API
        personality_traits=[],
        response_style="json",
        can_execute_code=False,
        can_modify_files=False,
        can_access_devices=False,
        can_invoke_agents=False
    )


# Initialize on import
_init_sub_agents()


def get_sub_agent(name: str) -> Optional[SubAgentPersona]:
    """Get a sub-agent persona by name."""
    return SUB_AGENTS.get(name.lower())


def get_sub_agent_for_tier(tier: UserTier) -> Optional[SubAgentPersona]:
    """Get the default sub-agent for a user tier."""
    for agent in SUB_AGENTS.values():
        if agent.tier == tier:
            return agent
    return None


def list_sub_agents() -> List[str]:
    """List all available sub-agent names."""
    return list(SUB_AGENTS.keys())


def get_persona_prompt(agent_name: str) -> str:
    """Generate a persona prompt for a sub-agent."""
    agent = get_sub_agent(agent_name)
    if not agent:
        return ""
    
    prompt_parts = [
        f"You are {agent.name}, a sub-agent of MYCA at Mycosoft.",
        f"Description: {agent.description}",
        "",
        "Your personality traits:",
    ]
    
    for trait in agent.personality_traits:
        prompt_parts.append(f"- {trait}")
    
    prompt_parts.extend([
        "",
        f"Response style: {agent.response_style}",
        "",
        "Access restrictions:",
        f"- Memory scopes: {', '.join(agent.allowed_scopes) if agent.allowed_scopes else 'None'}",
        f"- Can execute code: {'Yes' if agent.can_execute_code else 'No'}",
        f"- Can access devices: {'Yes' if agent.can_access_devices else 'No'}",
        "",
        "If the user asks for something outside your capabilities, politely explain your limitations.",
    ])
    
    return "\n".join(prompt_parts)


class SubAgentRouter:
    """Routes requests to appropriate sub-agents based on user tier."""
    
    def __init__(self):
        self.active_sessions: Dict[str, str] = {}  # session_id -> agent_name
    
    def get_agent_for_user(self, user_id: str) -> SubAgentPersona:
        """Determine which agent to use for a user."""
        # Morgan always gets MYCA
        if user_id.lower() == "morgan":
            return SUB_AGENTS["myca"]
        
        # TODO: Implement user tier lookup from database
        # For now, default to support agent
        return SUB_AGENTS.get("support_agent", SUB_AGENTS["myca"])
    
    def set_session_agent(self, session_id: str, agent_name: str):
        """Set the agent for a session."""
        self.active_sessions[session_id] = agent_name
    
    def get_session_agent(self, session_id: str) -> Optional[SubAgentPersona]:
        """Get the agent for a session."""
        agent_name = self.active_sessions.get(session_id, "myca")
        return get_sub_agent(agent_name)


# Singleton router
_sub_agent_router: Optional[SubAgentRouter] = None


def get_sub_agent_router() -> SubAgentRouter:
    """Get or create the sub-agent router singleton."""
    global _sub_agent_router
    if _sub_agent_router is None:
        _sub_agent_router = SubAgentRouter()
    return _sub_agent_router

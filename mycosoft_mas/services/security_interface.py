from typing import Dict, Any, Protocol, runtime_checkable

@runtime_checkable
class AgentSecurable(Protocol):
    """Interface for objects that can be secured by the SecurityService."""
    
    def get_agent_id(self) -> str:
        """Get the unique identifier of the agent."""
        ...
    
    def get_name(self) -> str:
        """Get the display name of the agent."""
        ...
    
    def get_capabilities(self) -> list[str]:
        """Get the capabilities of the agent."""
        ...
    
    def get_security_token(self) -> str:
        """Get the current security token of the agent."""
        ...
    
    def set_security_token(self, token: str) -> None:
        """Set the security token for the agent."""
        ... 
from typing import Dict, Any, Protocol, runtime_checkable

@runtime_checkable
class AgentInterface(Protocol):
    """Interface that all agents must implement."""
    
    agent_id: str
    name: str
    status: str
    config: Dict[str, Any]
    
    async def initialize(self, integration_service: Any) -> None:
        """Initialize the agent with the integration service."""
        ...
    
    async def start(self) -> None:
        """Start the agent's main processing loop."""
        ...
    
    async def stop(self) -> None:
        """Stop the agent's main processing loop."""
        ...
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current agent metrics."""
        ... 
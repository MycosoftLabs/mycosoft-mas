from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

class AgentInterface(ABC):
    """Base interface for all agents in the system."""
    
    @abstractmethod
    def get_id(self) -> str:
        """Get the unique identifier of the agent."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get the list of capabilities this agent has."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        pass
    
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task assigned to this agent."""
        pass
    
    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a message sent to this agent."""
        pass 
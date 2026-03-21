from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AgentInterface(ABC):
    """Base interface for all agents in the system."""

    @abstractmethod
    def get_id(self) -> str:
        """Get the unique identifier of the agent."""

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get the list of capabilities this agent has."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task assigned to this agent."""

    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a message sent to this agent."""

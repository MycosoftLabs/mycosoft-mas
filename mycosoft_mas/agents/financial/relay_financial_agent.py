"""
Relay Financial Agent for Mycosoft MAS.

Integrates Relay Financial for treasury, banking, and payments.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class RelayFinancialAgent(BaseAgent):
    """Agent for Relay Financial banking operations."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Relay Financial Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update({"banking", "treasury", "payments"})
        self.relay_api_key = os.getenv("RELAY_API_KEY", "")
        self.relay_base_url = os.getenv("RELAY_API_BASE_URL", "https://api.relayfi.com")

    async def _initialize_services(self) -> None:
        """Initialize Relay Financial client configuration."""
        if not self.relay_api_key:
            logger.warning("RELAY_API_KEY not set - Relay integration disabled")
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        """Return Relay integration health based on configuration."""
        return {
            "relay_configured": bool(self.relay_api_key),
            "relay_base_url": self.relay_base_url,
        }

    async def _check_resource_usage(self) -> Dict[str, Any]:
        """Relay agent has no local resource usage."""
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def process(self) -> None:
        """Idle loop; Relay actions are triggered via tasks/messages."""
        await asyncio.sleep(0.1)

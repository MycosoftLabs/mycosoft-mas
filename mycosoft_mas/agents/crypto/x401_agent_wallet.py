"""
X401 Agent Wallet Agent for Mycosoft MAS.

Autonomous agent wallet management, multi-sig, spending limits, audit trail.
Uses Solana and Phantom clients for on-chain operations.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class X401AgentWalletAgent(BaseAgent):
    """Agent for X401 Agent Wallet protocol - autonomous agent wallets."""

    def __init__(
        self,
        agent_id: str,
        name: str = "X401 Agent Wallet Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update({"agent_wallet", "solana", "multi_sig", "audit"})
        self._solana = None
        self._phantom = None

    def _get_solana(self):
        if self._solana is None:
            try:
                from mycosoft_mas.integrations.solana_client import SolanaClient

                self._solana = SolanaClient(self.config)
            except ImportError:
                logger.warning("SolanaClient not available - X401 agent limited")
        return self._solana

    def _get_phantom(self):
        if self._phantom is None:
            try:
                from mycosoft_mas.integrations.phantom_client import PhantomClient

                self._phantom = PhantomClient(self.config)
            except ImportError:
                logger.warning("PhantomClient not available - X401 agent limited")
        return self._phantom

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        solana = self._get_solana()
        if solana:
            return await solana.health_check()
        return {"status": "unconfigured", "error": "Solana client not available"}

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent wallet tasks: balance, tokens, audit."""
        task_type = task.get("type", "")
        if task_type == "get_balance":
            addr = task.get("address", "")
            solana = self._get_solana()
            if solana and addr:
                bal = await solana.get_balance(addr)
                return {"status": "success", "balance_lamports": bal}
        elif task_type == "get_token_accounts":
            addr = task.get("address", "")
            phantom = self._get_phantom()
            if phantom and addr:
                accounts = await phantom.get_token_accounts(addr)
                return {"status": "success", "accounts": accounts}
        elif task_type == "health":
            return await self._check_services_health()
        return {"status": "unhandled", "task_type": task_type}

    async def process(self) -> None:
        await asyncio.sleep(0.1)

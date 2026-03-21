"""
DAO Treasury Management Agent for Mycosoft MAS.

Multi-sig treasury operations, budget allocation, expense tracking,
financial reporting for MYCO DAO. Uses Solana, Jupiter, DEX clients.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class DAOTreasuryAgent(BaseAgent):
    """Agent for DAO treasury management."""

    def __init__(
        self,
        agent_id: str,
        name: str = "DAO Treasury Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update({"treasury", "multi_sig", "budget", "reporting"})
        self._solana = None
        self._dex = None

    def _get_solana(self):
        if self._solana is None:
            try:
                from mycosoft_mas.integrations.solana_client import SolanaClient

                self._solana = SolanaClient(self.config)
            except ImportError:
                pass
        return self._solana

    def _get_dex(self):
        if self._dex is None:
            try:
                from mycosoft_mas.integrations.solana_dex_client import SolanaDexClient

                self._dex = SolanaDexClient(self.config)
            except ImportError:
                pass
        return self._dex

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        dex = self._get_dex()
        if dex:
            return await dex.health_check()
        solana = self._get_solana()
        if solana:
            return await solana.health_check()
        return {"status": "unconfigured"}

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle treasury tasks: pools, balance, report."""
        task_type = task.get("type", "")
        if task_type == "list_pools":
            dex = self._get_dex()
            if dex:
                pools = await dex.raydium_pools()
                return {"status": "success", "pools": pools}
        elif task_type == "get_treasury_balance":
            addr = task.get("address", "")
            solana = self._get_solana()
            if solana and addr:
                bal = await solana.get_balance(addr)
                tokens = await solana.get_token_accounts(addr)
                return {"status": "success", "balance_lamports": bal, "token_accounts": tokens}
        return {"status": "unhandled", "task_type": task_type}

    async def process(self) -> None:
        await asyncio.sleep(0.1)

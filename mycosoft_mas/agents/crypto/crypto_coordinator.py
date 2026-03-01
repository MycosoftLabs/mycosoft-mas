"""
Mycosoft MAS - Crypto Coordinator Agent
Created: March 1, 2026

Master coordinator for all cryptocurrency operations in the Mycosoft MAS.
Routes tasks to appropriate sub-agents, manages portfolio-wide operations,
and provides unified crypto intelligence to Myca and other agents.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork

logger = logging.getLogger(__name__)


# Token to agent mapping
TOKEN_AGENT_MAP = {
    "BTC": "bitcoin_agent",
    "ETH": "ethereum_agent",
    "SOL": "solana_agent",
    "AVAX": "avalanche_agent",
    "AAVE": "aave_agent",
    "USDT": "tether_agent",
    "USDC": "usdcoin_agent",
    "XRP": "ripple_agent",
    "BNB": "bnb_agent",
    "XAUT": "tether_gold_agent",
    "UNI": "uniswap_agent",
}

SUPPORTED_TOKENS = list(TOKEN_AGENT_MAP.keys())

ALL_AGENT_IDS = [
    # Token agents
    "bitcoin_agent",
    "ethereum_agent",
    "solana_agent",
    "avalanche_agent",
    "aave_agent",
    "tether_agent",
    "usdcoin_agent",
    "ripple_agent",
    "bnb_agent",
    "tether_gold_agent",
    "uniswap_agent",
    # DeFi agents
    "liquidity_pool_agent",
    "raydium_agent",
    "dex_aggregator_agent",
    # Wallet agents
    "phantom_wallet_agent",
    "metamask_wallet_agent",
    "coinbase_wallet_agent",
    "edge_wallet_agent",
    "agentic_wallet_agent",
    # DAO agents
    "realms_dao_agent",
    "governance_tools_agent",
    # Protocol agents
    "x402_protocol_agent",
]


class CryptoCoordinatorAgent(BaseAgent):
    """
    Master Crypto Coordinator Agent.

    Orchestrates all cryptocurrency operations across the MAS:

    Sub-agents managed:
    - 11 Token Agents (BTC, ETH, SOL, AVAX, AAVE, USDT, USDC, XRP, BNB, XAUT, UNI)
    - 3 DeFi Agents (Liquidity Pools, Raydium, DEX Aggregator)
    - 5 Wallet Agents (Phantom, MetaMask, Coinbase/CDP, Edge, Agentic Wallet)
    - 2 DAO Agents (Realms, Governance Tools)
    - 1 Protocol Agent (x402 Payments)

    Total: 22 crypto sub-agents

    Capabilities:
    - Portfolio-wide price monitoring and alerts
    - Cross-chain asset tracking
    - Unified transaction history
    - Risk assessment and spending guardrails
    - DeFi yield optimization across protocols
    - DAO governance coordination
    - x402 payment orchestration
    - Integration with MycoDAO and TokenEconomics agents
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)

        self.capabilities = {
            "crypto_portfolio",
            "crypto_prices",
            "crypto_send",
            "crypto_swap",
            "crypto_defi",
            "crypto_dao",
            "crypto_x402",
            "crypto_wallets",
            "crypto_analytics",
            "crypto_alerts",
        }

        # Sub-agent registry (populated during initialization)
        self.sub_agents: Dict[str, Any] = {}

        # Portfolio tracking
        self.portfolio: Dict[str, Dict[str, Any]] = {}

        # Alert thresholds
        self.price_alerts: Dict[str, Dict[str, float]] = {}

        self.logger = logging.getLogger("crypto.coordinator")

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False

        self.logger.info(
            f"CryptoCoordinatorAgent initialized. "
            f"Managing {len(ALL_AGENT_IDS)} crypto sub-agents."
        )
        return True

    def register_sub_agent(self, agent_id: str, agent: Any) -> None:
        """Register a crypto sub-agent with the coordinator."""
        self.sub_agents[agent_id] = agent
        self.logger.info(f"Registered sub-agent: {agent_id}")

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get a comprehensive market overview of all tracked tokens."""
        overview = {
            "timestamp": datetime.utcnow().isoformat(),
            "tokens": {},
            "total_market_cap": 0,
        }

        # Fetch prices for all supported tokens
        for token in SUPPORTED_TOKENS:
            agent_id = TOKEN_AGENT_MAP.get(token)
            agent = self.sub_agents.get(agent_id)
            if agent and hasattr(agent, "get_price"):
                price_data = await agent.get_price(token)
                overview["tokens"][token] = {
                    "price": price_data.get("price", 0),
                    "change_24h": price_data.get("change_24h", 0),
                    "market_cap": price_data.get("market_cap", 0),
                }
                overview["total_market_cap"] += price_data.get("market_cap", 0)

        return overview

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get unified portfolio summary across all wallets."""
        total_value = Decimal("0")
        holdings = {}

        for token, data in self.portfolio.items():
            amount = Decimal(str(data.get("amount", 0)))
            agent_id = TOKEN_AGENT_MAP.get(token)
            agent = self.sub_agents.get(agent_id)

            price = Decimal("0")
            if agent and hasattr(agent, "get_price"):
                price_data = await agent.get_price(token)
                price = Decimal(str(price_data.get("price", 0)))

            value = amount * price
            total_value += value
            holdings[token] = {
                "amount": str(amount),
                "price": str(price),
                "value": str(value),
                "wallets": data.get("wallets", []),
            }

        return {
            "total_value_usd": str(total_value),
            "holdings": holdings,
            "token_count": len(holdings),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def route_to_agent(
        self, agent_id: str, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route a task to a specific sub-agent."""
        agent = self.sub_agents.get(agent_id)
        if not agent:
            return {
                "error": f"Sub-agent {agent_id} not found or not registered"
            }

        try:
            return await agent.process_task(task)
        except Exception as e:
            self.logger.error(f"Error routing to {agent_id}: {e}")
            return {"error": str(e)}

    async def set_price_alert(
        self,
        token: str,
        above: Optional[float] = None,
        below: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Set price alert thresholds for a token."""
        alert = {}
        if above is not None:
            alert["above"] = above
        if below is not None:
            alert["below"] = below

        self.price_alerts[token.upper()] = alert
        return {
            "success": True,
            "token": token.upper(),
            "alert": alert,
        }

    async def check_price_alerts(self) -> List[Dict[str, Any]]:
        """Check all price alerts and return triggered ones."""
        triggered = []

        for token, thresholds in self.price_alerts.items():
            agent_id = TOKEN_AGENT_MAP.get(token)
            agent = self.sub_agents.get(agent_id)
            if not agent or not hasattr(agent, "get_price"):
                continue

            price_data = await agent.get_price(token)
            price = price_data.get("price", 0)

            if "above" in thresholds and price >= thresholds["above"]:
                triggered.append({
                    "token": token,
                    "type": "above",
                    "threshold": thresholds["above"],
                    "current_price": price,
                })
            if "below" in thresholds and price <= thresholds["below"]:
                triggered.append({
                    "token": token,
                    "type": "below",
                    "threshold": thresholds["below"],
                    "current_price": price,
                })

        return triggered

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all crypto sub-agents."""
        status = {
            "coordinator": "active",
            "sub_agents": {},
            "total_registered": len(self.sub_agents),
            "total_expected": len(ALL_AGENT_IDS),
            "supported_tokens": SUPPORTED_TOKENS,
            "supported_chains": [c.value for c in ChainNetwork],
        }

        for agent_id in ALL_AGENT_IDS:
            agent = self.sub_agents.get(agent_id)
            status["sub_agents"][agent_id] = (
                "registered" if agent else "not_registered"
            )

        return status

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming tasks for the crypto coordinator."""
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        handlers = {
            "crypto_market_overview": self._handle_market_overview,
            "crypto_portfolio": self._handle_portfolio,
            "crypto_route": self._handle_route,
            "crypto_alert_set": self._handle_set_alert,
            "crypto_alert_check": self._handle_check_alerts,
            "crypto_status": self._handle_status,
            "crypto_price": self._handle_price,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(payload)

        return {"status": "error", "message": f"Unknown task: {task_type}"}

    async def _handle_market_overview(self, _payload: Dict) -> Dict:
        return {"status": "success", "result": await self.get_market_overview()}

    async def _handle_portfolio(self, _payload: Dict) -> Dict:
        return {"status": "success", "result": await self.get_portfolio_summary()}

    async def _handle_route(self, payload: Dict) -> Dict:
        agent_id = payload.get("agent_id", "")
        sub_task = payload.get("task", {})
        return {"status": "success", "result": await self.route_to_agent(agent_id, sub_task)}

    async def _handle_set_alert(self, payload: Dict) -> Dict:
        return {
            "status": "success",
            "result": await self.set_price_alert(
                payload.get("token", "BTC"),
                payload.get("above"),
                payload.get("below"),
            ),
        }

    async def _handle_check_alerts(self, _payload: Dict) -> Dict:
        return {"status": "success", "result": await self.check_price_alerts()}

    async def _handle_status(self, _payload: Dict) -> Dict:
        return {"status": "success", "result": self.get_system_status()}

    async def _handle_price(self, payload: Dict) -> Dict:
        token = payload.get("token", "BTC")
        agent_id = TOKEN_AGENT_MAP.get(token.upper())
        agent = self.sub_agents.get(agent_id)
        if agent and hasattr(agent, "get_price"):
            price_data = await agent.get_price(token)
            if "timestamp" in price_data and hasattr(price_data["timestamp"], "isoformat"):
                price_data["timestamp"] = price_data["timestamp"].isoformat()
            return {"status": "success", "result": price_data}
        return {"status": "error", "message": f"No agent for token {token}"}

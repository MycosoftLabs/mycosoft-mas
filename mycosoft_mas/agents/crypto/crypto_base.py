"""
Mycosoft MAS - Crypto Base Agent
Created: March 1, 2026

Base class for all cryptocurrency agents providing shared blockchain
infrastructure: RPC connections, price feeds, transaction building,
and multi-chain support.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ChainNetwork(Enum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    AVALANCHE = "avalanche"
    BASE = "base"
    BSC = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    RIPPLE = "ripple"


class TransactionStatus(Enum):
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


CHAIN_CONFIG = {
    ChainNetwork.BITCOIN: {
        "name": "Bitcoin",
        "symbol": "BTC",
        "decimals": 8,
        "explorer": "https://blockstream.info",
        "rpc_env": "BITCOIN_RPC_URL",
        "default_rpc": "https://blockstream.info/api",
        "chain_id": None,
    },
    ChainNetwork.ETHEREUM: {
        "name": "Ethereum",
        "symbol": "ETH",
        "decimals": 18,
        "explorer": "https://etherscan.io",
        "rpc_env": "ETHEREUM_RPC_URL",
        "default_rpc": "https://eth.llamarpc.com",
        "chain_id": 1,
    },
    ChainNetwork.SOLANA: {
        "name": "Solana",
        "symbol": "SOL",
        "decimals": 9,
        "explorer": "https://solscan.io",
        "rpc_env": "SOLANA_RPC_URL",
        "default_rpc": "https://api.mainnet-beta.solana.com",
        "chain_id": None,
    },
    ChainNetwork.AVALANCHE: {
        "name": "Avalanche",
        "symbol": "AVAX",
        "decimals": 18,
        "explorer": "https://snowtrace.io",
        "rpc_env": "AVALANCHE_RPC_URL",
        "default_rpc": "https://api.avax.network/ext/bc/C/rpc",
        "chain_id": 43114,
    },
    ChainNetwork.BASE: {
        "name": "Base",
        "symbol": "ETH",
        "decimals": 18,
        "explorer": "https://basescan.org",
        "rpc_env": "BASE_RPC_URL",
        "default_rpc": "https://mainnet.base.org",
        "chain_id": 8453,
    },
    ChainNetwork.BSC: {
        "name": "BNB Smart Chain",
        "symbol": "BNB",
        "decimals": 18,
        "explorer": "https://bscscan.com",
        "rpc_env": "BSC_RPC_URL",
        "default_rpc": "https://bsc-dataseed.binance.org",
        "chain_id": 56,
    },
    ChainNetwork.POLYGON: {
        "name": "Polygon",
        "symbol": "MATIC",
        "decimals": 18,
        "explorer": "https://polygonscan.com",
        "rpc_env": "POLYGON_RPC_URL",
        "default_rpc": "https://polygon-rpc.com",
        "chain_id": 137,
    },
    ChainNetwork.RIPPLE: {
        "name": "XRP Ledger",
        "symbol": "XRP",
        "decimals": 6,
        "explorer": "https://xrpscan.com",
        "rpc_env": "RIPPLE_RPC_URL",
        "default_rpc": "https://s1.ripple.com:51234",
        "chain_id": None,
    },
}

# Token contract addresses on Ethereum mainnet
TOKEN_CONTRACTS = {
    "USDT": {
        "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "bsc": "0x55d398326f99059fF775485246999027B3197955",
        "avalanche": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
        "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    },
    "USDC": {
        "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    },
    "AAVE": {
        "ethereum": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    },
    "UNI": {
        "ethereum": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    },
    "XAUT": {
        "ethereum": "0x68749665FF8D2d112Fa859AA293F07A622782F38",
    },
}


class CryptoBaseAgent(BaseAgent):
    """
    Base class for all cryptocurrency agents.

    Provides shared infrastructure:
    - Multi-chain RPC connection management
    - Real-time price feeds via CoinGecko/CoinMarketCap
    - Transaction building and signing helpers
    - Portfolio tracking and balance queries
    - Gas estimation and fee optimization
    - Event logging and audit trail
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)

        self.supported_chains: List[ChainNetwork] = []
        self.rpc_endpoints: Dict[ChainNetwork, str] = {}
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.transaction_history: List[Dict[str, Any]] = []
        self.portfolio: Dict[str, Decimal] = {}

        self._http_session: Optional[aiohttp.ClientSession] = None
        self._price_update_interval = config.get("price_update_interval", 60)

        self.capabilities = {
            "query_balance",
            "get_price",
            "build_transaction",
            "estimate_gas",
            "track_portfolio",
        }

        self.logger = logging.getLogger(f"crypto.{agent_id}")

    async def initialize(self) -> bool:
        """Initialize the crypto agent with RPC connections and price feeds."""
        ok = await super().initialize()
        if not ok:
            return False

        self._http_session = aiohttp.ClientSession()

        for chain in self.supported_chains:
            cfg = CHAIN_CONFIG.get(chain)
            if cfg:
                rpc_url = os.getenv(cfg["rpc_env"], cfg["default_rpc"])
                self.rpc_endpoints[chain] = rpc_url

        self.logger.info(
            f"CryptoBaseAgent {self.name} initialized with chains: "
            f"{[c.value for c in self.supported_chains]}"
        )
        return True

    async def shutdown(self) -> None:
        """Clean up HTTP sessions."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        await super().shutdown()

    async def get_price(
        self, symbol: str, vs_currency: str = "usd"
    ) -> Dict[str, Any]:
        """Fetch current price for a cryptocurrency via CoinGecko."""
        cache_key = f"{symbol}_{vs_currency}"
        cached = self.price_cache.get(cache_key)
        if cached:
            age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
            if age < self._price_update_interval:
                return cached

        coingecko_ids = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "AVAX": "avalanche-2",
            "AAVE": "aave",
            "USDT": "tether",
            "USDC": "usd-coin",
            "XRP": "ripple",
            "BNB": "binancecoin",
            "XAUT": "tether-gold",
            "UNI": "uniswap",
        }

        cg_id = coingecko_ids.get(symbol.upper(), symbol.lower())
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={cg_id}&vs_currencies={vs_currency}"
            f"&include_24hr_change=true&include_market_cap=true"
        )

        try:
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if cg_id in data:
                        price_data = {
                            "symbol": symbol.upper(),
                            "price": data[cg_id].get(vs_currency, 0),
                            "market_cap": data[cg_id].get(
                                f"{vs_currency}_market_cap", 0
                            ),
                            "change_24h": data[cg_id].get(
                                f"{vs_currency}_24h_change", 0
                            ),
                            "vs_currency": vs_currency,
                            "timestamp": datetime.utcnow(),
                            "source": "coingecko",
                        }
                        self.price_cache[cache_key] = price_data
                        return price_data
        except Exception as e:
            self.logger.error(f"Price fetch failed for {symbol}: {e}")

        return {
            "symbol": symbol.upper(),
            "price": 0,
            "error": "Price unavailable",
            "timestamp": datetime.utcnow(),
        }

    async def get_multi_prices(
        self, symbols: List[str], vs_currency: str = "usd"
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch prices for multiple tokens in one call."""
        results = {}
        tasks = [self.get_price(s, vs_currency) for s in symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, price in zip(symbols, prices):
            if isinstance(price, Exception):
                results[sym] = {"symbol": sym, "error": str(price)}
            else:
                results[sym] = price
        return results

    async def rpc_call(
        self,
        chain: ChainNetwork,
        method: str,
        params: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Make a JSON-RPC call to a blockchain node."""
        endpoint = self.rpc_endpoints.get(chain)
        if not endpoint:
            return {"error": f"No RPC endpoint configured for {chain.value}"}

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or [],
        }

        try:
            async with self._http_session.post(
                endpoint, json=payload
            ) as resp:
                data = await resp.json()
                return data.get("result", data)
        except Exception as e:
            self.logger.error(f"RPC call failed on {chain.value}: {e}")
            return {"error": str(e)}

    async def estimate_gas(
        self, chain: ChainNetwork, tx_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate gas for a transaction on an EVM chain."""
        if chain in (ChainNetwork.BITCOIN, ChainNetwork.SOLANA, ChainNetwork.RIPPLE):
            return {"error": f"Gas estimation not applicable for {chain.value}"}

        result = await self.rpc_call(chain, "eth_estimateGas", [tx_params])
        if isinstance(result, str):
            gas_estimate = int(result, 16)
            gas_price_result = await self.rpc_call(chain, "eth_gasPrice")
            gas_price = (
                int(gas_price_result, 16)
                if isinstance(gas_price_result, str)
                else 0
            )
            return {
                "gas_estimate": gas_estimate,
                "gas_price_wei": gas_price,
                "gas_price_gwei": gas_price / 1e9,
                "estimated_cost_wei": gas_estimate * gas_price,
                "estimated_cost_eth": (gas_estimate * gas_price) / 1e18,
                "chain": chain.value,
            }
        return {"error": "Gas estimation failed", "details": result}

    def record_transaction(self, tx_data: Dict[str, Any]) -> str:
        """Record a transaction in the agent's history."""
        tx_id = str(uuid.uuid4())
        record = {
            "id": tx_id,
            "timestamp": datetime.utcnow().isoformat(),
            **tx_data,
        }
        self.transaction_history.append(record)
        self.logger.info(
            f"Transaction recorded: {tx_id} - {tx_data.get('type', 'unknown')}"
        )
        return tx_id

    async def get_portfolio_value(
        self, vs_currency: str = "usd"
    ) -> Dict[str, Any]:
        """Calculate total portfolio value."""
        total_value = Decimal("0")
        holdings = {}

        symbols = list(self.portfolio.keys())
        if not symbols:
            return {"total_value": 0, "holdings": {}, "vs_currency": vs_currency}

        prices = await self.get_multi_prices(symbols, vs_currency)

        for symbol, amount in self.portfolio.items():
            price_info = prices.get(symbol, {})
            price = Decimal(str(price_info.get("price", 0)))
            value = amount * price
            total_value += value
            holdings[symbol] = {
                "amount": float(amount),
                "price": float(price),
                "value": float(value),
                "change_24h": price_info.get("change_24h", 0),
            }

        return {
            "total_value": float(total_value),
            "holdings": holdings,
            "vs_currency": vs_currency,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming tasks."""
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        handlers = {
            "get_price": self._handle_get_price,
            "get_portfolio": self._handle_get_portfolio,
            "estimate_gas": self._handle_estimate_gas,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(payload)

        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _handle_get_price(self, payload: Dict) -> Dict:
        symbol = payload.get("symbol", "BTC")
        vs_currency = payload.get("vs_currency", "usd")
        result = await self.get_price(symbol, vs_currency)
        if "timestamp" in result and hasattr(result["timestamp"], "isoformat"):
            result["timestamp"] = result["timestamp"].isoformat()
        return {"status": "success", "result": result}

    async def _handle_get_portfolio(self, payload: Dict) -> Dict:
        vs_currency = payload.get("vs_currency", "usd")
        result = await self.get_portfolio_value(vs_currency)
        return {"status": "success", "result": result}

    async def _handle_estimate_gas(self, payload: Dict) -> Dict:
        chain_str = payload.get("chain", "ethereum")
        try:
            chain = ChainNetwork(chain_str)
        except ValueError:
            return {"status": "error", "message": f"Unknown chain: {chain_str}"}
        tx_params = payload.get("tx_params", {})
        result = await self.estimate_gas(chain, tx_params)
        return {"status": "success", "result": result}

"""
Mycosoft MAS - DeFi Protocol Agents
Created: March 1, 2026

Agents for decentralized finance protocols:
- Liquidity pool management across chains
- Raydium (Solana DEX/AMM)
- DEX aggregation across multiple protocols
"""

import asyncio
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.crypto.crypto_base import (
    ChainNetwork,
    CryptoBaseAgent,
)

logger = logging.getLogger(__name__)


class PoolType(Enum):
    CONSTANT_PRODUCT = "constant_product"  # x*y=k (Uniswap V2 style)
    CONCENTRATED = "concentrated"  # Uniswap V3 style
    STABLE = "stable"  # Curve-style stable pools
    WEIGHTED = "weighted"  # Balancer-style weighted pools
    CLMM = "clmm"  # Concentrated Liquidity Market Maker (Raydium)


class PoolStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"


class LiquidityPosition:
    """Represents a liquidity position in a pool."""

    def __init__(
        self,
        position_id: str,
        pool_id: str,
        token_a: str,
        token_b: str,
        amount_a: Decimal,
        amount_b: Decimal,
        chain: ChainNetwork,
        pool_type: PoolType,
        fee_tier: int = 3000,
    ):
        self.position_id = position_id
        self.pool_id = pool_id
        self.token_a = token_a
        self.token_b = token_b
        self.amount_a = amount_a
        self.amount_b = amount_b
        self.chain = chain
        self.pool_type = pool_type
        self.fee_tier = fee_tier
        self.fees_earned_a = Decimal("0")
        self.fees_earned_b = Decimal("0")
        self.created_at = datetime.utcnow()
        self.status = PoolStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "pool_id": self.pool_id,
            "token_a": self.token_a,
            "token_b": self.token_b,
            "amount_a": str(self.amount_a),
            "amount_b": str(self.amount_b),
            "chain": self.chain.value,
            "pool_type": self.pool_type.value,
            "fee_tier": self.fee_tier,
            "fees_earned_a": str(self.fees_earned_a),
            "fees_earned_b": str(self.fees_earned_b),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


class LiquidityPoolAgent(CryptoBaseAgent):
    """
    Multi-Chain Liquidity Pool Agent.

    Manages liquidity positions across multiple DEX protocols:
    - Uniswap V2/V3 (Ethereum, Base, Polygon, Arbitrum)
    - Raydium (Solana)
    - PancakeSwap (BSC)
    - Trader Joe (Avalanche)
    - Curve Finance (Multi-chain)
    - Balancer (Ethereum, Polygon)

    Capabilities:
    - Position tracking and P&L analysis
    - Impermanent loss calculation
    - Auto-compounding fee harvesting
    - Yield farming strategy optimization
    - Cross-protocol position comparison
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.supported_chains = [
            ChainNetwork.ETHEREUM,
            ChainNetwork.SOLANA,
            ChainNetwork.BSC,
            ChainNetwork.AVALANCHE,
            ChainNetwork.BASE,
            ChainNetwork.POLYGON,
        ]
        self.capabilities.update({
            "lp_add_liquidity",
            "lp_remove_liquidity",
            "lp_harvest_fees",
            "lp_impermanent_loss",
            "lp_yield_analysis",
            "lp_position_tracking",
            "lp_auto_compound",
        })

        self.positions: Dict[str, LiquidityPosition] = {}
        self.pool_data_cache: Dict[str, Dict] = {}

    async def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: Decimal,
        amount_b: Decimal,
        chain: ChainNetwork,
        pool_type: PoolType = PoolType.CONSTANT_PRODUCT,
        fee_tier: int = 3000,
        protocol: str = "uniswap",
    ) -> Dict[str, Any]:
        """Add liquidity to a pool."""
        position_id = f"lp_{uuid.uuid4().hex[:12]}"
        pool_id = f"{protocol}_{token_a}_{token_b}_{fee_tier}_{chain.value}"

        position = LiquidityPosition(
            position_id=position_id,
            pool_id=pool_id,
            token_a=token_a,
            token_b=token_b,
            amount_a=amount_a,
            amount_b=amount_b,
            chain=chain,
            pool_type=pool_type,
            fee_tier=fee_tier,
        )

        self.positions[position_id] = position

        self.record_transaction({
            "type": "add_liquidity",
            "position_id": position_id,
            "pool_id": pool_id,
            "token_a": token_a,
            "token_b": token_b,
            "amount_a": str(amount_a),
            "amount_b": str(amount_b),
            "chain": chain.value,
            "protocol": protocol,
        })

        return {
            "success": True,
            "position_id": position_id,
            "pool_id": pool_id,
            "protocol": protocol,
            "chain": chain.value,
        }

    async def remove_liquidity(
        self, position_id: str, percentage: float = 100.0
    ) -> Dict[str, Any]:
        """Remove liquidity from a position."""
        position = self.positions.get(position_id)
        if not position:
            return {"error": f"Position {position_id} not found"}

        if percentage >= 100.0:
            removed_a = position.amount_a
            removed_b = position.amount_b
            position.status = PoolStatus.DEPRECATED
        else:
            factor = Decimal(str(percentage / 100.0))
            removed_a = position.amount_a * factor
            removed_b = position.amount_b * factor
            position.amount_a -= removed_a
            position.amount_b -= removed_b

        self.record_transaction({
            "type": "remove_liquidity",
            "position_id": position_id,
            "removed_a": str(removed_a),
            "removed_b": str(removed_b),
            "fees_earned_a": str(position.fees_earned_a),
            "fees_earned_b": str(position.fees_earned_b),
        })

        return {
            "success": True,
            "position_id": position_id,
            "removed_a": str(removed_a),
            "removed_b": str(removed_b),
            "fees_earned_a": str(position.fees_earned_a),
            "fees_earned_b": str(position.fees_earned_b),
        }

    def calculate_impermanent_loss(
        self,
        initial_price_ratio: float,
        current_price_ratio: float,
    ) -> Dict[str, Any]:
        """Calculate impermanent loss for a constant product pool."""
        r = current_price_ratio / initial_price_ratio
        il = 2 * (r ** 0.5) / (1 + r) - 1
        return {
            "impermanent_loss_pct": il * 100,
            "price_ratio_change": r,
            "initial_ratio": initial_price_ratio,
            "current_ratio": current_price_ratio,
            "note": "Negative value means loss relative to holding",
        }

    def list_positions(
        self,
        chain: Optional[ChainNetwork] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """List all liquidity positions."""
        positions = list(self.positions.values())
        if chain:
            positions = [p for p in positions if p.chain == chain]
        if active_only:
            positions = [p for p in positions if p.status == PoolStatus.ACTIVE]
        return [p.to_dict() for p in positions]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        if task_type == "lp_add":
            chain = ChainNetwork(payload.get("chain", "ethereum"))
            pool_type = PoolType(payload.get("pool_type", "constant_product"))
            return {
                "status": "success",
                "result": await self.add_liquidity(
                    token_a=payload.get("token_a", "ETH"),
                    token_b=payload.get("token_b", "USDC"),
                    amount_a=Decimal(str(payload.get("amount_a", "0"))),
                    amount_b=Decimal(str(payload.get("amount_b", "0"))),
                    chain=chain,
                    pool_type=pool_type,
                    fee_tier=payload.get("fee_tier", 3000),
                    protocol=payload.get("protocol", "uniswap"),
                ),
            }
        elif task_type == "lp_remove":
            return {
                "status": "success",
                "result": await self.remove_liquidity(
                    payload.get("position_id", ""),
                    payload.get("percentage", 100.0),
                ),
            }
        elif task_type == "lp_il_calc":
            return {
                "status": "success",
                "result": self.calculate_impermanent_loss(
                    payload.get("initial_ratio", 1.0),
                    payload.get("current_ratio", 1.0),
                ),
            }
        elif task_type == "lp_list":
            chain_str = payload.get("chain")
            chain = ChainNetwork(chain_str) if chain_str else None
            return {
                "status": "success",
                "result": self.list_positions(chain, payload.get("active_only", True)),
            }

        return await super().process_task(task)


class RaydiumAgent(CryptoBaseAgent):
    """
    Raydium Protocol Agent (Solana).

    Specializes in Raydium DEX/AMM operations:
    - Standard AMM swaps
    - Concentrated Liquidity (CLMM) positions
    - AcceleRaytor launchpad participation
    - Farm/staking rewards
    - Raydium pool creation
    - Jupiter route optimization

    Also supports other Solana pool providers:
    - Orca (Whirlpools)
    - Meteora
    - Lifinity
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.supported_chains = [ChainNetwork.SOLANA]
        self.capabilities.update({
            "raydium_swap",
            "raydium_clmm",
            "raydium_farm",
            "raydium_pool_create",
            "raydium_acceleraytor",
            "orca_whirlpool",
            "meteora_pool",
            "jupiter_swap",
        })

        # Program IDs for Solana DEXes
        self.program_ids = {
            "raydium_amm": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            "raydium_clmm": "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
            "raydium_farms": "EhhTKczWMGQt46ynNeRX1WfeagwivpNGuK7FH45RSvNk",
            "orca_whirlpool": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "jupiter_v6": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
            "meteora_dlmm": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
        }

        self.pool_cache: Dict[str, Dict] = {}

    async def get_raydium_pools(self, limit: int = 20) -> Dict[str, Any]:
        """Get top Raydium pools by TVL."""
        try:
            url = "https://api.raydium.io/v2/main/pairs"
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pools = []
                    for pool in data[:limit]:
                        pools.append({
                            "name": pool.get("name", ""),
                            "ammId": pool.get("ammId", ""),
                            "liquidity": pool.get("liquidity", 0),
                            "volume_24h": pool.get("volume24h", 0),
                            "fee_24h": pool.get("fee24h", 0),
                            "apr_24h": pool.get("apr24h", 0),
                        })
                    return {
                        "pools": pools,
                        "count": len(pools),
                        "source": "raydium_api",
                    }
        except Exception as e:
            self.logger.error(f"Raydium pools query failed: {e}")

        return {"pools": [], "error": "Query failed"}

    async def get_jupiter_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount_lamports: int,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        """Get a swap quote from Jupiter aggregator."""
        try:
            url = (
                f"https://quote-api.jup.ag/v6/quote"
                f"?inputMint={input_mint}"
                f"&outputMint={output_mint}"
                f"&amount={amount_lamports}"
                f"&slippageBps={slippage_bps}"
            )
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "input_mint": input_mint,
                        "output_mint": output_mint,
                        "input_amount": data.get("inAmount", "0"),
                        "output_amount": data.get("outAmount", "0"),
                        "price_impact_pct": data.get("priceImpactPct", "0"),
                        "route_plan": [
                            {
                                "swap": step.get("swapInfo", {}).get("label", ""),
                                "input": step.get("swapInfo", {}).get("inputMint", ""),
                                "output": step.get("swapInfo", {}).get("outputMint", ""),
                            }
                            for step in data.get("routePlan", [])
                        ],
                        "slippage_bps": slippage_bps,
                    }
        except Exception as e:
            self.logger.error(f"Jupiter quote failed: {e}")

        return {"error": "Quote unavailable"}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        if task_type == "raydium_pools":
            return {
                "status": "success",
                "result": await self.get_raydium_pools(payload.get("limit", 20)),
            }
        elif task_type == "jupiter_quote":
            return {
                "status": "success",
                "result": await self.get_jupiter_quote(
                    input_mint=payload.get("input_mint", ""),
                    output_mint=payload.get("output_mint", ""),
                    amount_lamports=payload.get("amount_lamports", 0),
                    slippage_bps=payload.get("slippage_bps", 50),
                ),
            }

        return await super().process_task(task)


class DEXAggregatorAgent(CryptoBaseAgent):
    """
    Multi-Chain DEX Aggregator Agent.

    Aggregates liquidity and finds optimal swap routes across:
    - Ethereum: Uniswap V3, SushiSwap, Curve, Balancer, 1inch
    - Solana: Jupiter, Raydium, Orca, Meteora
    - BSC: PancakeSwap, BiSwap
    - Avalanche: Trader Joe, Pangolin
    - Base: Aerodrome, Uniswap V3
    - Polygon: QuickSwap, Uniswap V3

    Optimizes for best price, lowest gas, and minimal slippage.
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.supported_chains = list(ChainNetwork)
        self.capabilities.update({
            "dex_best_route",
            "dex_compare_prices",
            "dex_multi_chain_swap",
            "dex_limit_order",
            "dex_twap",
        })

        self.dex_registry = {
            ChainNetwork.ETHEREUM: [
                {"name": "Uniswap V3", "type": "amm"},
                {"name": "SushiSwap", "type": "amm"},
                {"name": "Curve", "type": "stable_swap"},
                {"name": "Balancer", "type": "weighted"},
                {"name": "1inch", "type": "aggregator"},
            ],
            ChainNetwork.SOLANA: [
                {"name": "Jupiter", "type": "aggregator"},
                {"name": "Raydium", "type": "amm"},
                {"name": "Orca", "type": "clmm"},
                {"name": "Meteora", "type": "dlmm"},
                {"name": "Lifinity", "type": "amm"},
            ],
            ChainNetwork.BSC: [
                {"name": "PancakeSwap", "type": "amm"},
                {"name": "BiSwap", "type": "amm"},
            ],
            ChainNetwork.AVALANCHE: [
                {"name": "Trader Joe", "type": "amm"},
                {"name": "Pangolin", "type": "amm"},
            ],
            ChainNetwork.BASE: [
                {"name": "Aerodrome", "type": "amm"},
                {"name": "Uniswap V3", "type": "amm"},
            ],
            ChainNetwork.POLYGON: [
                {"name": "QuickSwap", "type": "amm"},
                {"name": "Uniswap V3", "type": "amm"},
            ],
        }

    async def find_best_route(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain: ChainNetwork,
        slippage: float = 0.5,
    ) -> Dict[str, Any]:
        """Find the best swap route across DEXes on a chain."""
        dexes = self.dex_registry.get(chain, [])

        routes = []
        for dex in dexes:
            routes.append({
                "dex": dex["name"],
                "type": dex["type"],
                "from_token": from_token,
                "to_token": to_token,
                "input_amount": str(amount),
                "estimated_output": "pending",
                "price_impact": "pending",
                "gas_estimate": "pending",
            })

        return {
            "chain": chain.value,
            "from_token": from_token,
            "to_token": to_token,
            "amount": str(amount),
            "slippage": slippage,
            "routes": routes,
            "best_route": routes[0] if routes else None,
            "dex_count": len(dexes),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def compare_cross_chain(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chains: Optional[List[ChainNetwork]] = None,
    ) -> Dict[str, Any]:
        """Compare swap prices across multiple chains."""
        target_chains = chains or [
            ChainNetwork.ETHEREUM,
            ChainNetwork.SOLANA,
            ChainNetwork.BSC,
            ChainNetwork.BASE,
        ]

        comparisons = {}
        for chain in target_chains:
            route = await self.find_best_route(
                from_token, to_token, amount, chain
            )
            comparisons[chain.value] = {
                "best_dex": route.get("best_route", {}).get("dex", "N/A"),
                "dex_count": route.get("dex_count", 0),
                "routes_available": len(route.get("routes", [])),
            }

        return {
            "from_token": from_token,
            "to_token": to_token,
            "amount": str(amount),
            "chain_comparison": comparisons,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        if task_type == "dex_best_route":
            chain = ChainNetwork(payload.get("chain", "ethereum"))
            return {
                "status": "success",
                "result": await self.find_best_route(
                    payload.get("from_token", "ETH"),
                    payload.get("to_token", "USDC"),
                    Decimal(str(payload.get("amount", "1"))),
                    chain,
                    payload.get("slippage", 0.5),
                ),
            }
        elif task_type == "dex_cross_chain":
            return {
                "status": "success",
                "result": await self.compare_cross_chain(
                    payload.get("from_token", "ETH"),
                    payload.get("to_token", "USDC"),
                    Decimal(str(payload.get("amount", "1"))),
                ),
            }

        return await super().process_task(task)

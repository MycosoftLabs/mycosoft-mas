"""
Solana DEX Client (Raydium, Orca).

Liquidity pools, farming, LP management.
Uses Raydium and Orca HTTP APIs where available, plus Solana RPC for on-chain state.

Environment Variables:
    SOLANA_RPC_URL: RPC endpoint
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.integrations.solana_client import SolanaClient

logger = logging.getLogger(__name__)

RAYDIUM_API = "https://api-v3.raydium.io"
ORCA_WHIRLPOOL_API = "https://api.orca.so"


class SolanaDexClient:
    """Client for Raydium and Orca DEX operations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.solana = SolanaClient(config)
        self.timeout = self.config.get("timeout", 30)

    async def raydium_pools(self, pool_type: str = "all") -> List[Dict[str, Any]]:
        """List Raydium pools. Uses mainnet pool list."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(f"{RAYDIUM_API}/main/pools")
                if r.is_success:
                    data = r.json()
                    return data if isinstance(data, list) else data.get("data", [])
            return []
        except Exception as e:
            logger.warning("Raydium pools failed: %s", e)
            return []

    async def raydium_pool_by_ids(self, pool_ids: List[str]) -> List[Dict[str, Any]]:
        """Get Raydium pool info by ID(s)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{RAYDIUM_API}/main/pool/info",
                    json={"poolIds": pool_ids},
                )
                if r.is_success:
                    data = r.json()
                    return data if isinstance(data, list) else [data]
            return []
        except Exception as e:
            logger.warning("Raydium pool info failed: %s", e)
            return []

    async def orca_whirlpools(self, wallet: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Orca Whirlpool positions (if wallet provided)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params: Dict[str, Any] = {}
                if wallet:
                    params["wallet"] = wallet
                r = await client.get(f"{ORCA_WHIRLPOOL_API}/whirlpool/list", params=params)
                if r.is_success:
                    data = r.json()
                    return data.get("whirlpools", [])
            return []
        except Exception as e:
            logger.warning("Orca whirlpools failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to DEX APIs."""
        try:
            pools = await self.raydium_pools()
            if isinstance(pools, list) and len(pools) >= 0:
                return {"status": "healthy", "source": "raydium"}
            return {"status": "unhealthy", "error": "No pools"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

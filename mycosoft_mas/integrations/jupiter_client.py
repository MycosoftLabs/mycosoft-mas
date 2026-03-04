"""
Jupiter DEX Integration Client (Solana).

Token swaps, price quotes, route optimization.
Jupiter aggregates Solana DEX liquidity.

Environment Variables:
    SOLANA_RPC_URL: Optional RPC for swap execution
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_PRICE_API = "https://price.jup.ag/v6/price"


class JupiterClient:
    """Client for Jupiter DEX API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> Optional[Dict[str, Any]]:
        """
        Get swap quote. amount in smallest unit (lamports for SOL).
        input_mint/output_mint: SPL token mint addresses.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(
                    JUPITER_QUOTE_API,
                    params={
                        "inputMint": input_mint,
                        "outputMint": output_mint,
                        "amount": str(amount),
                        "slippageBps": slippage_bps,
                    },
                )
                if r.is_success:
                    return r.json()
            return None
        except Exception as e:
            logger.warning("Jupiter get_quote failed: %s", e)
            return None

    async def get_price(
        self,
        ids: Optional[List[str]] = None,
        vs_token: str = "So11111111111111111111111111111111111111112",
    ) -> Optional[Dict[str, Any]]:
        """Get price for token(s). ids = list of mint addresses."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params: Dict[str, Any] = {"vsToken": vs_token}
                if ids:
                    params["ids"] = ",".join(ids)
                r = await client.get(JUPITER_PRICE_API, params=params)
                if r.is_success:
                    return r.json()
            return None
        except Exception as e:
            logger.warning("Jupiter get_price failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Jupiter API."""
        try:
            prices = await self.get_price(ids=["So11111111111111111111111111111111111111112"])
            if prices and "data" in prices:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "No price data"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

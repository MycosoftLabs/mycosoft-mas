"""
Solana On-Chain Integration Client.

Wallet operations, SOL/SPL token transfers, MYCO token, transaction signing.
Uses Solana JSON-RPC. Used by crypto agents and X401 Agent Wallet.

Environment Variables:
    SOLANA_RPC_URL: RPC endpoint (default https://api.mainnet-beta.solana.com)
    SOLANA_WALLET_PRIVATE_KEY: Base58 private key for signing (optional)
"""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SOLANA_RPC_DEFAULT = "https://api.mainnet-beta.solana.com"


class SolanaClient:
    """Client for Solana JSON-RPC API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rpc_url = self.config.get(
            "rpc_url", os.environ.get("SOLANA_RPC_URL", SOLANA_RPC_DEFAULT)
        )
        self.private_key_b58 = self.config.get(
            "private_key", os.environ.get("SOLANA_WALLET_PRIVATE_KEY", "")
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _rpc(self, method: str, params: Optional[List[Any]] = None) -> Optional[Any]:
        """Call Solana JSON-RPC."""
        client = await self._get_client()
        try:
            r = await client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
            )
            if r.is_success:
                data = r.json()
                if "error" in data:
                    logger.warning("Solana RPC error: %s", data["error"])
                    return None
                return data.get("result")
            return None
        except Exception as e:
            logger.warning("Solana RPC failed: %s", e)
            return None

    async def get_balance(self, address: str) -> Optional[int]:
        """Get SOL balance in lamports."""
        result = await self._rpc("getBalance", [address])
        if result is not None and "value" in result:
            return result["value"]
        return None

    async def get_token_accounts(
        self, wallet_address: str
    ) -> List[Dict[str, Any]]:
        """Get SPL token accounts for a wallet."""
        result = await self._rpc(
            "getTokenAccountsByOwner",
            [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}],
        )
        if not result or "value" not in result:
            return []
        return result["value"]

    async def get_recent_blockhash(self) -> Optional[str]:
        """Get recent blockhash for transaction construction."""
        result = await self._rpc("getLatestBlockhash")
        if result and "value" in result:
            return result["value"].get("blockhash")
        return None

    async def send_transaction(self, serialized_tx: str) -> Optional[str]:
        """Send a signed transaction (base64 encoded). Returns signature or None."""
        result = await self._rpc("sendTransaction", [serialized_tx, {"encoding": "base64"}])
        return result if isinstance(result, str) else None

    async def get_signature_status(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get transaction status."""
        result = await self._rpc("getSignatureStatuses", [[signature]])
        if result and "value" in result and result["value"]:
            return result["value"][0]
        return None

    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account info."""
        result = await self._rpc("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        return result

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Solana RPC."""
        try:
            bh = await self.get_recent_blockhash()
            if bh:
                return {"status": "healthy", "blockhash": bh[:16] + "..."}
            return {"status": "unhealthy", "error": "No blockhash"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

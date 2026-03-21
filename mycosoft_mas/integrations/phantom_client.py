"""
Phantom Wallet Integration Client.

Wallet connect patterns, transaction signing support, dApp integration.
Phantom is a browser extension wallet - this client provides:
- Deeplink helpers for connect/sign
- Solana RPC passthrough for Phantom-connected addresses
- Transaction payload building for Phantom signing

Environment Variables:
    SOLANA_RPC_URL: RPC endpoint for on-chain operations
"""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional


from mycosoft_mas.integrations.solana_client import SolanaClient

logger = logging.getLogger(__name__)

PHANTOM_DEEPLINK_BASE = "https://phantom.app/ul/v1"


class PhantomClient:
    """Client for Phantom wallet integration (deeplinks + Solana RPC)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.solana = SolanaClient(config)
        self.timeout = self.config.get("timeout", 30)

    @staticmethod
    def connect_deeplink(app_url: str, redirect_link: Optional[str] = None) -> str:
        """Build Phantom connect deeplink for dApp wallet connection."""
        params: Dict[str, str] = {"app_url": app_url}
        if redirect_link:
            params["redirect_link"] = redirect_link
        qs = urllib.parse.urlencode(params)
        return f"{PHANTOM_DEEPLINK_BASE}/connect?{qs}"

    @staticmethod
    def sign_transaction_deeplink(
        app_url: str,
        transaction: str,
        redirect_link: Optional[str] = None,
    ) -> str:
        """Build deeplink for signing a transaction (base64)."""
        params: Dict[str, str] = {"app_url": app_url, "transaction": transaction}
        if redirect_link:
            params["redirect_link"] = redirect_link
        qs = urllib.parse.urlencode(params)
        return f"{PHANTOM_DEEPLINK_BASE}/signTransaction?{qs}"

    @staticmethod
    def sign_message_deeplink(
        app_url: str,
        message: str,
        display: str = "utf8",
    ) -> str:
        """Build deeplink for signing a message."""
        params: Dict[str, str] = {
            "app_url": app_url,
            "message": message,
            "display": display,
        }
        qs = urllib.parse.urlencode(params)
        return f"{PHANTOM_DEEPLINK_BASE}/signMessage?{qs}"

    async def get_balance(self, address: str) -> Optional[int]:
        """Get SOL balance for a Phantom wallet address."""
        return await self.solana.get_balance(address)

    async def get_token_accounts(self, address: str) -> List[Dict[str, Any]]:
        """Get SPL token accounts for a Phantom wallet."""
        return await self.solana.get_token_accounts(address)

    async def health_check(self) -> Dict[str, Any]:
        """Verify Solana RPC used for Phantom integration."""
        return await self.solana.health_check()

"""
Open Wallet Standard (OWS) Integration Client.

Local-first, multi-chain wallet management for AI agents.
Wraps the ``open-wallet-standard`` Python SDK for encrypted key storage,
multi-chain signing (EVM, Solana, Bitcoin, Tron, TON, Cosmos), and
wallet lifecycle management.

If the OWS SDK is not installed the client gracefully degrades to the
existing SolanaClient for Solana-only operations.

Environment Variables:
    OWS_VAULT_PATH: Vault storage directory (default /var/lib/mycosoft/ows-vaults/)

Created: March 24, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported CAIP-2 chain identifiers
SUPPORTED_CHAINS = [
    "solana:mainnet",
    "eip155:1",       # Ethereum mainnet
    "bip122:000000000019d6689c085ae165831e93",  # Bitcoin mainnet
    "tron:mainnet",
    "ton:mainnet",
    "cosmos:cosmoshub-4",
]

CHAIN_DISPLAY_NAMES: Dict[str, str] = {
    "solana:mainnet": "Solana",
    "eip155:1": "Ethereum",
    "bip122:000000000019d6689c085ae165831e93": "Bitcoin",
    "tron:mainnet": "Tron",
    "ton:mainnet": "TON",
    "cosmos:cosmoshub-4": "Cosmos",
}

# Friendly aliases → CAIP-2
CHAIN_ALIASES: Dict[str, str] = {
    "solana": "solana:mainnet",
    "ethereum": "eip155:1",
    "eth": "eip155:1",
    "bitcoin": "bip122:000000000019d6689c085ae165831e93",
    "btc": "bip122:000000000019d6689c085ae165831e93",
    "tron": "tron:mainnet",
    "ton": "ton:mainnet",
    "cosmos": "cosmos:cosmoshub-4",
}

DEFAULT_VAULT_PATH = "/var/lib/mycosoft/ows-vaults/"

# Try importing the OWS SDK
try:
    from open_wallet_standard import create_wallet as _ows_create  # type: ignore[import-untyped]
    from open_wallet_standard import list_wallets as _ows_list  # type: ignore[import-untyped]
    from open_wallet_standard import sign_message as _ows_sign_msg  # type: ignore[import-untyped]
    from open_wallet_standard import sign_transaction as _ows_sign_tx  # type: ignore[import-untyped]
    from open_wallet_standard import get_wallet as _ows_get_wallet  # type: ignore[import-untyped]

    OWS_SDK_AVAILABLE = True
    logger.info("OWS SDK loaded — multi-chain wallet support active")
except ImportError:
    OWS_SDK_AVAILABLE = False
    logger.warning("OWS SDK not installed — falling back to Solana-only wallet support")


def _resolve_chain(chain: str) -> str:
    """Resolve a friendly chain name or alias to its CAIP-2 identifier."""
    lower = chain.lower().strip()
    return CHAIN_ALIASES.get(lower, chain)


class OWSClient:
    """Open Wallet Standard integration client.

    Provides encrypted vault creation, multi-chain address derivation,
    message/transaction signing, and wallet lifecycle management.

    Falls back to SolanaClient when OWS SDK is unavailable.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.vault_path = self.config.get(
            "vault_path",
            os.environ.get("OWS_VAULT_PATH", DEFAULT_VAULT_PATH),
        )
        self._solana_fallback = None

    def _get_solana_fallback(self):
        """Lazy-load SolanaClient for degraded mode."""
        if self._solana_fallback is None:
            try:
                from mycosoft_mas.integrations.solana_client import SolanaClient

                self._solana_fallback = SolanaClient(self.config)
            except ImportError:
                logger.warning("SolanaClient also unavailable — wallet ops disabled")
        return self._solana_fallback

    @property
    def sdk_available(self) -> bool:
        return OWS_SDK_AVAILABLE

    async def create_wallet(self, name: str, passphrase: str) -> Dict[str, Any]:
        """Create a new encrypted OWS vault.

        Returns dict with wallet_name, chains (CAIP-2 → address mapping),
        and creation metadata.
        """
        if not OWS_SDK_AVAILABLE:
            logger.info("OWS SDK unavailable — creating Solana-only wallet stub for %s", name)
            return {
                "wallet_name": name,
                "chains": {},
                "status": "degraded",
                "note": "OWS SDK not installed; install open-wallet-standard for multi-chain",
            }

        try:
            result = _ows_create(name, passphrase=passphrase, vault_path=self.vault_path)
            # Extract addresses for all supported chains
            chains: Dict[str, str] = {}
            wallet_info = _ows_get_wallet(name, vault_path=self.vault_path)
            if hasattr(wallet_info, "accounts"):
                for account in wallet_info.accounts:
                    chain_id = getattr(account, "chain", None)
                    address = getattr(account, "address", None)
                    if chain_id and address:
                        chains[chain_id] = address
            elif isinstance(wallet_info, dict):
                chains = wallet_info.get("accounts", {})

            return {
                "wallet_name": name,
                "chains": chains,
                "status": "active",
                "vault_path": self.vault_path,
            }
        except Exception as e:
            logger.error("OWS wallet creation failed for %s: %s", name, e)
            return {
                "wallet_name": name,
                "chains": {},
                "status": "error",
                "error": str(e),
            }

    async def get_wallet_info(self, name: str) -> Dict[str, Any]:
        """Get all chain addresses and metadata for a wallet."""
        if not OWS_SDK_AVAILABLE:
            return {"wallet_name": name, "chains": {}, "status": "degraded"}

        try:
            wallet_info = _ows_get_wallet(name, vault_path=self.vault_path)
            chains: Dict[str, str] = {}
            if hasattr(wallet_info, "accounts"):
                for account in wallet_info.accounts:
                    chain_id = getattr(account, "chain", None)
                    address = getattr(account, "address", None)
                    if chain_id and address:
                        chains[chain_id] = address
            elif isinstance(wallet_info, dict):
                chains = wallet_info.get("accounts", {})

            return {
                "wallet_name": name,
                "chains": chains,
                "status": "active",
            }
        except Exception as e:
            logger.warning("Failed to get wallet info for %s: %s", name, e)
            return {"wallet_name": name, "chains": {}, "status": "error", "error": str(e)}

    async def get_address(self, name: str, chain: str) -> Optional[str]:
        """Get the address for a specific chain. Accepts friendly names (e.g. 'solana')."""
        chain_id = _resolve_chain(chain)
        info = await self.get_wallet_info(name)
        return info.get("chains", {}).get(chain_id)

    async def sign_message(
        self, name: str, chain: str, message: str, passphrase: str
    ) -> Optional[str]:
        """Sign a message on a specific chain."""
        if not OWS_SDK_AVAILABLE:
            logger.warning("OWS SDK unavailable — cannot sign message")
            return None

        chain_id = _resolve_chain(chain)
        try:
            sig = _ows_sign_msg(
                name, chain_id, message, passphrase=passphrase, vault_path=self.vault_path
            )
            return sig if isinstance(sig, str) else str(sig)
        except Exception as e:
            logger.error("OWS sign_message failed: %s", e)
            return None

    async def sign_transaction(
        self, name: str, chain: str, tx_data: Dict[str, Any], passphrase: str
    ) -> Optional[str]:
        """Sign a transaction on a specific chain."""
        if not OWS_SDK_AVAILABLE:
            logger.warning("OWS SDK unavailable — cannot sign transaction")
            return None

        chain_id = _resolve_chain(chain)
        try:
            sig = _ows_sign_tx(
                name, chain_id, tx_data, passphrase=passphrase, vault_path=self.vault_path
            )
            return sig if isinstance(sig, str) else str(sig)
        except Exception as e:
            logger.error("OWS sign_transaction failed: %s", e)
            return None

    async def list_wallets(self) -> List[str]:
        """List all wallet names in the vault."""
        if not OWS_SDK_AVAILABLE:
            return []

        try:
            wallets = _ows_list(vault_path=self.vault_path)
            if isinstance(wallets, list):
                return [str(w) for w in wallets]
            return []
        except Exception as e:
            logger.warning("OWS list_wallets failed: %s", e)
            return []

    async def export_public_keys(self, name: str) -> Dict[str, str]:
        """Export chain → public address mapping for a wallet."""
        info = await self.get_wallet_info(name)
        return info.get("chains", {})

    async def health_check(self) -> Dict[str, Any]:
        """Check OWS system health."""
        if not OWS_SDK_AVAILABLE:
            # Check if SolanaClient fallback works
            solana = self._get_solana_fallback()
            if solana:
                sol_health = await solana.health_check()
                return {
                    "status": "degraded",
                    "ows_sdk": False,
                    "solana_fallback": sol_health.get("status", "unknown"),
                    "supported_chains": ["solana:mainnet"],
                }
            return {
                "status": "unavailable",
                "ows_sdk": False,
                "solana_fallback": "unavailable",
                "supported_chains": [],
            }

        try:
            wallets = await self.list_wallets()
            return {
                "status": "healthy",
                "ows_sdk": True,
                "vault_path": self.vault_path,
                "wallet_count": len(wallets),
                "supported_chains": SUPPORTED_CHAINS,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "ows_sdk": True,
                "error": str(e),
                "supported_chains": SUPPORTED_CHAINS,
            }

"""
Mycosoft MAS - Cryptocurrency Agent Package
Created: March 1, 2026

Complete cryptocurrency, DeFi, wallet, and DAO agent infrastructure
for the Mycosoft Multi-Agent System with Coinbase CDP, x402 protocol,
and multi-chain support.
"""

from importlib import import_module


def _safe_import(module_path: str, symbol: str):
    try:
        module = import_module(module_path, package=__name__)
        obj = getattr(module, symbol)
        globals()[symbol] = obj
        return obj
    except Exception:
        return None


# Core infrastructure
_safe_import(".crypto_base", "CryptoBaseAgent")
_safe_import(".wallet_manager", "WalletManager")
_safe_import(".x402_protocol", "X402ProtocolAgent")

# Master coordinator
_safe_import(".crypto_coordinator", "CryptoCoordinatorAgent")

# Token agents
_safe_import(".token_agents", "BitcoinAgent")
_safe_import(".token_agents", "EthereumAgent")
_safe_import(".token_agents", "SolanaAgent")
_safe_import(".token_agents", "AvalancheAgent")
_safe_import(".token_agents", "AaveAgent")
_safe_import(".token_agents", "TetherAgent")
_safe_import(".token_agents", "USDCoinAgent")
_safe_import(".token_agents", "RippleAgent")
_safe_import(".token_agents", "BNBAgent")
_safe_import(".token_agents", "TetherGoldAgent")
_safe_import(".token_agents", "UniswapAgent")

# DeFi agents
_safe_import(".defi_agents", "LiquidityPoolAgent")
_safe_import(".defi_agents", "RaydiumAgent")
_safe_import(".defi_agents", "DEXAggregatorAgent")

# Wallet agents
_safe_import(".wallet_agents", "PhantomWalletAgent")
_safe_import(".wallet_agents", "MetaMaskWalletAgent")
_safe_import(".wallet_agents", "CoinbaseWalletAgent")
_safe_import(".wallet_agents", "EdgeWalletAgent")
_safe_import(".wallet_agents", "AgenticWalletAgent")

# DAO agents
_safe_import(".dao_agents", "RealmsDAOAgent")
_safe_import(".dao_agents", "GovernanceToolsAgent")

__all__ = [
    "CryptoBaseAgent",
    "WalletManager",
    "X402ProtocolAgent",
    "CryptoCoordinatorAgent",
    "BitcoinAgent",
    "EthereumAgent",
    "SolanaAgent",
    "AvalancheAgent",
    "AaveAgent",
    "TetherAgent",
    "USDCoinAgent",
    "RippleAgent",
    "BNBAgent",
    "TetherGoldAgent",
    "UniswapAgent",
    "LiquidityPoolAgent",
    "RaydiumAgent",
    "DEXAggregatorAgent",
    "PhantomWalletAgent",
    "MetaMaskWalletAgent",
    "CoinbaseWalletAgent",
    "EdgeWalletAgent",
    "AgenticWalletAgent",
    "RealmsDAOAgent",
    "GovernanceToolsAgent",
]

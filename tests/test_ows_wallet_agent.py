"""
Tests for OWS Wallet Agent and OWS Client.

Created: March 24, 2026
"""

from __future__ import annotations

import pytest

from mycosoft_mas.integrations.ows_client import (
    CHAIN_ALIASES,
    CHAIN_DISPLAY_NAMES,
    SUPPORTED_CHAINS,
    OWSClient,
    _resolve_chain,
)


# ---------------------------------------------------------------------------
# OWS Client unit tests
# ---------------------------------------------------------------------------


class TestOWSClientInit:
    def test_client_creation(self):
        client = OWSClient()
        assert client.vault_path is not None

    def test_client_with_config(self):
        client = OWSClient(config={"vault_path": "/tmp/test-vaults"})
        assert client.vault_path == "/tmp/test-vaults"

    def test_sdk_available_attribute(self):
        client = OWSClient()
        assert isinstance(client.sdk_available, bool)


class TestChainResolution:
    def test_resolve_solana(self):
        assert _resolve_chain("solana") == "solana:mainnet"

    def test_resolve_ethereum(self):
        assert _resolve_chain("ethereum") == "eip155:1"
        assert _resolve_chain("eth") == "eip155:1"

    def test_resolve_bitcoin(self):
        assert _resolve_chain("bitcoin") == "bip122:000000000019d6689c085ae165831e93"
        assert _resolve_chain("btc") == "bip122:000000000019d6689c085ae165831e93"

    def test_resolve_passthrough(self):
        assert _resolve_chain("eip155:1") == "eip155:1"
        assert _resolve_chain("unknown:chain") == "unknown:chain"

    def test_resolve_case_insensitive(self):
        assert _resolve_chain("SOLANA") == "solana:mainnet"
        assert _resolve_chain("Ethereum") == "eip155:1"


class TestConstants:
    def test_supported_chains_populated(self):
        assert len(SUPPORTED_CHAINS) >= 6
        assert "solana:mainnet" in SUPPORTED_CHAINS
        assert "eip155:1" in SUPPORTED_CHAINS

    def test_chain_display_names(self):
        assert CHAIN_DISPLAY_NAMES["solana:mainnet"] == "Solana"
        assert CHAIN_DISPLAY_NAMES["eip155:1"] == "Ethereum"

    def test_chain_aliases(self):
        assert "solana" in CHAIN_ALIASES
        assert "eth" in CHAIN_ALIASES
        assert "btc" in CHAIN_ALIASES


# ---------------------------------------------------------------------------
# OWS Client async tests (degraded mode — SDK not installed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_degraded():
    """Health check should work even without OWS SDK."""
    client = OWSClient()
    result = await client.health_check()
    assert "status" in result
    assert "ows_sdk" in result


@pytest.mark.asyncio
async def test_create_wallet_degraded():
    """Wallet creation should return degraded status without SDK."""
    client = OWSClient()
    if not client.sdk_available:
        result = await client.create_wallet("test-wallet", "test-pass")
        assert result["status"] == "degraded"
        assert "note" in result


@pytest.mark.asyncio
async def test_list_wallets_degraded():
    """List wallets should return empty list without SDK."""
    client = OWSClient()
    if not client.sdk_available:
        result = await client.list_wallets()
        assert result == []


@pytest.mark.asyncio
async def test_sign_message_degraded():
    """Sign message should return None without SDK."""
    client = OWSClient()
    if not client.sdk_available:
        result = await client.sign_message("test", "solana", "hello", "pass")
        assert result is None


@pytest.mark.asyncio
async def test_export_public_keys_degraded():
    """Export public keys should return empty dict without SDK."""
    client = OWSClient()
    if not client.sdk_available:
        result = await client.export_public_keys("test")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# OWS Wallet Agent unit tests
# ---------------------------------------------------------------------------


class TestOWSWalletAgentImport:
    def test_agent_importable(self):
        from mycosoft_mas.agents.crypto.ows_wallet_agent import OWSWalletAgent

        agent = OWSWalletAgent()
        assert agent.agent_id == "ows-wallet-agent"
        assert "ows_wallet" in agent.capabilities
        assert "multi_chain" in agent.capabilities
        assert "agent_payments" in agent.capabilities
        assert "treasury" in agent.capabilities

    def test_agent_in_crypto_init(self):
        from mycosoft_mas.agents.crypto import OWSWalletAgent

        assert OWSWalletAgent is not None

    def test_constants(self):
        from mycosoft_mas.agents.crypto.ows_wallet_agent import (
            TREASURY_AGENT_ID,
            TREASURY_FEE_PERCENT,
            TREASURY_WALLET_NAME,
        )

        assert TREASURY_WALLET_NAME == "myca-treasury"
        assert TREASURY_AGENT_ID == "myca-treasury"
        assert 0 < float(TREASURY_FEE_PERCENT) < 1


@pytest.mark.asyncio
async def test_agent_process_unhandled():
    from mycosoft_mas.agents.crypto.ows_wallet_agent import OWSWalletAgent

    agent = OWSWalletAgent()
    result = await agent.process_task({"type": "nonexistent_task"})
    assert result["status"] == "unhandled"


@pytest.mark.asyncio
async def test_agent_create_wallet_missing_params():
    from mycosoft_mas.agents.crypto.ows_wallet_agent import OWSWalletAgent

    agent = OWSWalletAgent()
    result = await agent.process_task({"type": "create_wallet"})
    assert result["status"] == "error"
    assert "required" in result["error"]


@pytest.mark.asyncio
async def test_agent_get_balance_missing_params():
    from mycosoft_mas.agents.crypto.ows_wallet_agent import OWSWalletAgent

    agent = OWSWalletAgent()
    result = await agent.process_task({"type": "get_balance"})
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# OWS Wallet API Router model tests
# ---------------------------------------------------------------------------


class TestAPIModels:
    def test_create_wallet_request(self):
        from mycosoft_mas.core.routers.ows_wallet_api import CreateWalletRequest

        req = CreateWalletRequest(agent_id="test-agent")
        assert req.agent_id == "test-agent"
        assert req.wallet_type == "internal"

    def test_transfer_request(self):
        from mycosoft_mas.core.routers.ows_wallet_api import TransferRequest

        req = TransferRequest(
            from_agent_id="agent-a", to_agent_id="agent-b", amount=1.5
        )
        assert req.currency == "SOL"
        assert req.amount == 1.5

    def test_treasury_response(self):
        from mycosoft_mas.core.routers.ows_wallet_api import TreasuryResponse

        resp = TreasuryResponse()
        assert resp.wallet_name == "myca-treasury"
        assert resp.active_wallets == 0


# ---------------------------------------------------------------------------
# RaaS model tests
# ---------------------------------------------------------------------------


class TestRaaSModels:
    def test_registration_response_has_wallet_fields(self):
        from mycosoft_mas.raas.models import AgentRegistrationResponse

        resp = AgentRegistrationResponse(
            agent_id="test",
            api_key="key",
            status="pending",
            wallet_name="ext-test",
            deposit_addresses={"solana": "addr1"},
            next_steps=["Step 1"],
        )
        assert resp.wallet_name == "ext-test"
        assert "solana" in resp.deposit_addresses
        assert len(resp.next_steps) == 1


# ---------------------------------------------------------------------------
# Economy store OWS function tests
# ---------------------------------------------------------------------------


class TestEconomyStoreOWS:
    def test_ows_functions_exist(self):
        from mycosoft_mas.core.persistence.economy_store import (
            get_ows_treasury_metrics,
            get_ows_wallet_balance,
            record_ows_transaction,
        )

        assert callable(get_ows_wallet_balance)
        assert callable(record_ows_transaction)
        assert callable(get_ows_treasury_metrics)

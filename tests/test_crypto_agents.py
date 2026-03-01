"""
Tests for the Mycosoft MAS Cryptocurrency Agent System.
Created: March 1, 2026

Tests cover:
- CryptoBaseAgent initialization and price feeds
- WalletManager wallet creation and spending limits
- X402ProtocolAgent payment handling
- Token agent instantiation (BTC, ETH, SOL, etc.)
- DeFi agent operations (liquidity, Raydium, DEX)
- Wallet agent connections (Phantom, MetaMask, Coinbase, Edge)
- DAO agent governance (Realms proposals and voting)
- CryptoCoordinatorAgent orchestration
- Crypto API router endpoints
"""

import asyncio
from decimal import Decimal

import pytest

# ---- Agent instantiation tests ----


def _make_config(**overrides):
    cfg = {"data_dir": "/tmp/test_crypto", "price_update_interval": 0}
    cfg.update(overrides)
    return cfg


class TestCryptoBaseAgent:
    def test_import(self):
        from mycosoft_mas.agents.crypto.crypto_base import CryptoBaseAgent, ChainNetwork, CHAIN_CONFIG
        assert CryptoBaseAgent is not None
        assert len(ChainNetwork) >= 8
        assert ChainNetwork.BITCOIN in CHAIN_CONFIG

    def test_instantiate(self):
        from mycosoft_mas.agents.crypto.crypto_base import CryptoBaseAgent, ChainNetwork
        agent = CryptoBaseAgent("test_crypto", "Test Crypto Agent", _make_config())
        assert agent.agent_id == "test_crypto"
        assert agent.name == "Test Crypto Agent"
        assert "get_price" in agent.capabilities


class TestWalletManager:
    def test_import(self):
        from mycosoft_mas.agents.crypto.wallet_manager import (
            WalletManager, WalletType, SpendingLimit, WalletEntry,
        )
        assert WalletManager is not None

    def test_spending_limit_check(self):
        from mycosoft_mas.agents.crypto.wallet_manager import SpendingLimit
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        limit = SpendingLimit(
            max_per_transaction=Decimal("100"),
            max_per_session=Decimal("500"),
            max_daily=Decimal("1000"),
            allowed_tokens=["USDC", "ETH"],
            allowed_chains=[ChainNetwork.BASE],
        )

        # Should pass
        result = limit.check_limit(Decimal("50"), "USDC", ChainNetwork.BASE)
        assert result["allowed"] is True

        # Should fail - wrong token
        result = limit.check_limit(Decimal("50"), "BTC", ChainNetwork.BASE)
        assert result["allowed"] is False

        # Should fail - over per-transaction
        result = limit.check_limit(Decimal("150"), "USDC", ChainNetwork.BASE)
        assert result["allowed"] is False

        # Should fail - wrong chain
        result = limit.check_limit(Decimal("50"), "USDC", ChainNetwork.ETHEREUM)
        assert result["allowed"] is False

    def test_spending_limit_record(self):
        from mycosoft_mas.agents.crypto.wallet_manager import SpendingLimit
        limit = SpendingLimit(max_per_session=Decimal("100"))
        limit.record_spend(Decimal("40"))
        assert limit.session_spent == Decimal("40")
        assert limit.daily_spent == Decimal("40")

    @pytest.mark.asyncio
    async def test_create_wallet(self):
        from mycosoft_mas.agents.crypto.wallet_manager import WalletManager, WalletType
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        mgr = WalletManager({"data_dir": "/tmp/test_wallets"})
        await mgr.initialize()

        result = await mgr.create_wallet(
            wallet_type=WalletType.HOT_WALLET,
            chains=[ChainNetwork.ETHEREUM],
            label="Test Wallet",
        )
        assert result["success"] is True
        assert "wallet_id" in result

        wallets = mgr.list_wallets()
        assert len(wallets) >= 1

        await mgr.shutdown()


class TestX402ProtocolAgent:
    def test_import(self):
        from mycosoft_mas.agents.crypto.x402_protocol import (
            X402ProtocolAgent, X402PaymentRequirement, PaymentScheme,
        )
        assert X402ProtocolAgent is not None

    def test_payment_requirement_serialization(self):
        from mycosoft_mas.agents.crypto.x402_protocol import X402PaymentRequirement, PaymentScheme
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        req = X402PaymentRequirement(
            amount=Decimal("0.50"),
            token="USDC",
            chain=ChainNetwork.BASE,
            recipient="0x1234567890abcdef",
            resource_url="https://api.example.com/data",
            scheme=PaymentScheme.USDC_BASE,
            description="Test payment",
        )
        header = req.to_header()
        parsed = X402PaymentRequirement.from_header(header)
        assert parsed.amount == Decimal("0.50")
        assert parsed.token == "USDC"
        assert parsed.chain == ChainNetwork.BASE

    def test_instantiate(self):
        from mycosoft_mas.agents.crypto.x402_protocol import X402ProtocolAgent
        agent = X402ProtocolAgent("x402_test", "x402 Test", _make_config(session_budget="50.00"))
        assert "x402_pay" in agent.capabilities
        assert agent.session_budget == Decimal("50.00")


class TestTokenAgents:
    def test_bitcoin_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import BitcoinAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = BitcoinAgent("btc_test", "Bitcoin Test", _make_config())
        assert ChainNetwork.BITCOIN in agent.supported_chains
        assert "btc_send" in agent.capabilities
        assert "btc_ordinals" in agent.capabilities

    def test_ethereum_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import EthereumAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = EthereumAgent("eth_test", "Ethereum Test", _make_config())
        assert ChainNetwork.ETHEREUM in agent.supported_chains
        assert ChainNetwork.BASE in agent.supported_chains
        assert "eth_contract_call" in agent.capabilities

    def test_solana_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import SolanaAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = SolanaAgent("sol_test", "Solana Test", _make_config())
        assert ChainNetwork.SOLANA in agent.supported_chains
        assert "sol_raydium_swap" in agent.capabilities
        assert "sol_realms_governance" in agent.capabilities

    def test_avalanche_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import AvalancheAgent
        agent = AvalancheAgent("avax_test", "Avalanche Test", _make_config())
        assert "avax_c_chain" in agent.capabilities

    def test_aave_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import AaveAgent
        agent = AaveAgent("aave_test", "Aave Test", _make_config())
        assert "aave_flash_loan" in agent.capabilities
        assert "aave_lend" in agent.capabilities

    def test_stablecoin_agents(self):
        from mycosoft_mas.agents.crypto.token_agents import TetherAgent, USDCoinAgent
        usdt = TetherAgent("usdt_test", "USDT Test", _make_config())
        usdc = USDCoinAgent("usdc_test", "USDC Test", _make_config())
        assert usdt.token_symbol == "USDT"
        assert usdc.token_symbol == "USDC"
        assert "usdc_x402_payment" in usdc.capabilities

    def test_ripple_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import RippleAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = RippleAgent("xrp_test", "XRP Test", _make_config())
        assert ChainNetwork.RIPPLE in agent.supported_chains
        assert "xrp_dex_order" in agent.capabilities

    def test_bnb_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import BNBAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = BNBAgent("bnb_test", "BNB Test", _make_config())
        assert ChainNetwork.BSC in agent.supported_chains

    def test_tether_gold_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import TetherGoldAgent
        agent = TetherGoldAgent("xaut_test", "XAUT Test", _make_config())
        assert agent.token_symbol == "XAUT"
        assert "xaut_gold_peg" in agent.capabilities

    def test_uniswap_agent(self):
        from mycosoft_mas.agents.crypto.token_agents import UniswapAgent
        agent = UniswapAgent("uni_test", "Uniswap Test", _make_config())
        assert "uni_swap" in agent.capabilities
        assert "uni_add_liquidity" in agent.capabilities


class TestDeFiAgents:
    def test_liquidity_pool_agent(self):
        from mycosoft_mas.agents.crypto.defi_agents import LiquidityPoolAgent
        agent = LiquidityPoolAgent("lp_test", "LP Test", _make_config())
        assert "lp_add_liquidity" in agent.capabilities
        assert "lp_impermanent_loss" in agent.capabilities

    def test_impermanent_loss_calculation(self):
        from mycosoft_mas.agents.crypto.defi_agents import LiquidityPoolAgent
        agent = LiquidityPoolAgent("lp_test", "LP Test", _make_config())
        result = agent.calculate_impermanent_loss(1.0, 2.0)
        assert "impermanent_loss_pct" in result
        # With 2x price change, IL should be negative
        assert result["impermanent_loss_pct"] < 0

    def test_raydium_agent(self):
        from mycosoft_mas.agents.crypto.defi_agents import RaydiumAgent
        agent = RaydiumAgent("ray_test", "Raydium Test", _make_config())
        assert "raydium_swap" in agent.capabilities
        assert "raydium_clmm" in agent.capabilities
        assert "jupiter_swap" in agent.capabilities
        assert "orca_whirlpool" in agent.capabilities

    def test_dex_aggregator_agent(self):
        from mycosoft_mas.agents.crypto.defi_agents import DEXAggregatorAgent
        agent = DEXAggregatorAgent("dex_test", "DEX Test", _make_config())
        assert "dex_best_route" in agent.capabilities
        assert "dex_multi_chain_swap" in agent.capabilities
        assert len(agent.dex_registry) >= 5


class TestWalletAgents:
    def test_phantom_agent(self):
        from mycosoft_mas.agents.crypto.wallet_agents import PhantomWalletAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = PhantomWalletAgent("phantom_test", "Phantom Test", _make_config())
        assert ChainNetwork.SOLANA in agent.supported_chains
        assert "phantom_connect" in agent.capabilities

    def test_metamask_agent(self):
        from mycosoft_mas.agents.crypto.wallet_agents import MetaMaskWalletAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = MetaMaskWalletAgent("mm_test", "MetaMask Test", _make_config())
        assert ChainNetwork.ETHEREUM in agent.supported_chains
        assert ChainNetwork.BASE in agent.supported_chains
        assert "metamask_connect" in agent.capabilities

    def test_coinbase_wallet_agent(self):
        from mycosoft_mas.agents.crypto.wallet_agents import CoinbaseWalletAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = CoinbaseWalletAgent("cb_test", "Coinbase Test", _make_config())
        assert ChainNetwork.BASE in agent.supported_chains
        assert "cdp_create_wallet" in agent.capabilities
        assert "cdp_x402_pay" in agent.capabilities

    def test_edge_wallet_agent(self):
        from mycosoft_mas.agents.crypto.wallet_agents import EdgeWalletAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = EdgeWalletAgent("edge_test", "Edge Test", _make_config())
        assert ChainNetwork.BITCOIN in agent.supported_chains
        assert ChainNetwork.SOLANA in agent.supported_chains
        assert "edge_fiat_onramp" in agent.capabilities

    def test_agentic_wallet_agent(self):
        from mycosoft_mas.agents.crypto.wallet_agents import AgenticWalletAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = AgenticWalletAgent("aw_test", "Agentic Wallet Test", _make_config())
        assert ChainNetwork.BASE in agent.supported_chains
        assert "agentic_authenticate" in agent.capabilities
        assert "agentic_pay_service" in agent.capabilities
        assert "agentic_monetize" in agent.capabilities


class TestDAOAgents:
    def test_realms_agent(self):
        from mycosoft_mas.agents.crypto.dao_agents import RealmsDAOAgent
        from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork
        agent = RealmsDAOAgent("realms_test", "Realms Test", _make_config())
        assert ChainNetwork.SOLANA in agent.supported_chains
        assert "realms_create_proposal" in agent.capabilities
        assert "realms_btc_plugin" in agent.capabilities
        assert "realms_ordinals_membership" in agent.capabilities

    @pytest.mark.asyncio
    async def test_realms_proposal_workflow(self):
        from mycosoft_mas.agents.crypto.dao_agents import (
            RealmsDAOAgent, GovernanceVote,
        )

        agent = RealmsDAOAgent("realms_test", "Realms Test", _make_config())

        # Create realm
        realm = await agent.create_realm(
            realm_name="MycoDAO Test",
            governance_token_mint="MYCOxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        )
        assert realm["success"] is True
        realm_id = realm["realm"]["realm_id"]

        # Create proposal
        proposal = await agent.create_proposal(
            realm_id=realm_id,
            title="Fund Development",
            description="Allocate 10000 MYCO tokens for crypto agent development",
        )
        assert proposal["success"] is True
        proposal_id = proposal["proposal"]["proposal_id"]

        # Start voting
        voting = await agent.start_voting(proposal_id)
        assert voting["success"] is True

        # Cast votes
        vote1 = await agent.vote_on_proposal(
            proposal_id, "member_1", GovernanceVote.YES, Decimal("100")
        )
        assert vote1["success"] is True

        vote2 = await agent.vote_on_proposal(
            proposal_id, "member_2", GovernanceVote.YES, Decimal("50")
        )
        assert vote2["success"] is True

        vote3 = await agent.vote_on_proposal(
            proposal_id, "member_3", GovernanceVote.NO, Decimal("30")
        )
        assert vote3["success"] is True

        # Get results
        results = await agent.get_proposal_results(proposal_id)
        assert results["tally"]["yes_pct"] > 50

    @pytest.mark.asyncio
    async def test_btc_ordinals_membership(self):
        from mycosoft_mas.agents.crypto.dao_agents import RealmsDAOAgent
        agent = RealmsDAOAgent("realms_test", "Realms Test", _make_config())

        realm = await agent.create_realm("TestDAO", "MYCOxxxxxxxxxx")
        realm_id = realm["realm"]["realm_id"]

        result = await agent.register_btc_ordinal_membership(
            realm_id=realm_id,
            inscription_id="abc123i0",
            btc_address="bc1qexample",
            solana_address="SOLexample123",
        )
        assert result["success"] is True
        assert "membership_id" in result

    def test_governance_tools_agent(self):
        from mycosoft_mas.agents.crypto.dao_agents import GovernanceToolsAgent
        agent = GovernanceToolsAgent("gov_test", "Governance Test", _make_config())
        assert "gov_snapshot_vote" in agent.capabilities
        assert "gov_multisig" in agent.capabilities
        assert "gov_delegate" in agent.capabilities


class TestCryptoCoordinator:
    def test_import(self):
        from mycosoft_mas.agents.crypto.crypto_coordinator import (
            CryptoCoordinatorAgent, SUPPORTED_TOKENS, ALL_AGENT_IDS,
        )
        assert len(SUPPORTED_TOKENS) == 11
        assert len(ALL_AGENT_IDS) == 22

    def test_instantiate(self):
        from mycosoft_mas.agents.crypto.crypto_coordinator import CryptoCoordinatorAgent
        agent = CryptoCoordinatorAgent("coord_test", "Crypto Coordinator", _make_config())
        assert "crypto_portfolio" in agent.capabilities
        assert "crypto_x402" in agent.capabilities

    def test_system_status(self):
        from mycosoft_mas.agents.crypto.crypto_coordinator import CryptoCoordinatorAgent
        agent = CryptoCoordinatorAgent("coord_test", "Crypto Coordinator", _make_config())
        status = agent.get_system_status()
        assert status["coordinator"] == "active"
        assert status["total_expected"] == 22
        assert "BTC" in status["supported_tokens"]
        assert "bitcoin" in status["supported_chains"]


class TestCryptoAPIRouter:
    def test_import(self):
        from mycosoft_mas.core.routers.crypto_api import router
        assert router is not None
        assert router.prefix == "/api/crypto"

    def test_routes_exist(self):
        from mycosoft_mas.core.routers.crypto_api import router
        routes = [r.path for r in router.routes]
        assert "/health" in routes
        assert "/status" in routes
        assert "/price/{symbol}" in routes
        assert "/wallets/agentic" in routes
        assert "/x402/budget" in routes
        assert "/dao/proposals" in routes


class TestAgentRegistryImports:
    def test_crypto_agents_importable(self):
        """Verify all crypto agents are importable via the agents package."""
        from mycosoft_mas.agents import (
            CryptoBaseAgent,
            CryptoCoordinatorAgent,
            BitcoinAgent,
            EthereumAgent,
            SolanaAgent,
            AvalancheAgent,
            AaveAgent,
            TetherAgent,
            USDCoinAgent,
            RippleAgent,
            BNBAgent,
            TetherGoldAgent,
            UniswapAgent,
            LiquidityPoolAgent,
            RaydiumAgent,
            DEXAggregatorAgent,
            PhantomWalletAgent,
            MetaMaskWalletAgent,
            CoinbaseWalletAgent,
            EdgeWalletAgent,
            AgenticWalletAgent,
            RealmsDAOAgent,
            GovernanceToolsAgent,
        )
        # All should be non-None (successfully imported)
        agents = [
            CryptoBaseAgent, CryptoCoordinatorAgent,
            BitcoinAgent, EthereumAgent, SolanaAgent,
            AvalancheAgent, AaveAgent, TetherAgent,
            USDCoinAgent, RippleAgent, BNBAgent,
            TetherGoldAgent, UniswapAgent,
            LiquidityPoolAgent, RaydiumAgent, DEXAggregatorAgent,
            PhantomWalletAgent, MetaMaskWalletAgent,
            CoinbaseWalletAgent, EdgeWalletAgent, AgenticWalletAgent,
            RealmsDAOAgent, GovernanceToolsAgent,
        ]
        for agent_cls in agents:
            assert agent_cls is not None, f"Agent class is None"

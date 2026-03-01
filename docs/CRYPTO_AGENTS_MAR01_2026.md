# Mycosoft MAS - Cryptocurrency Agent System

**Created:** March 1, 2026
**Author:** MYCA Coding Agent
**Status:** Active
**Module:** `mycosoft_mas/agents/crypto/`

## Overview

Complete cryptocurrency, DeFi, wallet, and DAO agent infrastructure for the Mycosoft Multi-Agent System. Provides 22 specialized crypto sub-agents coordinated by a master CryptoCoordinatorAgent, with 50+ API endpoints via the crypto router.

## Architecture

```
CryptoCoordinatorAgent (Master)
├── Token Agents (11)
│   ├── BitcoinAgent       - BTC: UTXO, Ordinals, Lightning, fee estimation
│   ├── EthereumAgent      - ETH: ERC-20/721, EIP-1559, ENS, L2 bridging
│   ├── SolanaAgent        - SOL: SPL tokens, Raydium, Jupiter, Realms
│   ├── AvalancheAgent     - AVAX: C-Chain, subnets, cross-chain
│   ├── AaveAgent          - AAVE: lending/borrowing, flash loans, V3
│   ├── TetherAgent        - USDT: multi-chain, peg monitoring
│   ├── USDCoinAgent       - USDC: Circle CCTP, x402 payments
│   ├── RippleAgent        - XRP: XRPL DEX, trust lines, escrow
│   ├── BNBAgent           - BNB: BEP-20, PancakeSwap, Venus
│   ├── TetherGoldAgent    - XAUT: gold-backed, peg verification
│   └── UniswapAgent       - UNI: V3 swaps, LP management, governance
│
├── DeFi Agents (3)
│   ├── LiquidityPoolAgent - Multi-chain LP management, IL calculation
│   ├── RaydiumAgent       - Solana DEX: CLMM, Jupiter, Orca, Meteora
│   └── DEXAggregatorAgent - Cross-chain route optimization
│
├── Wallet Agents (5)
│   ├── PhantomWalletAgent    - Solana wallet integration
│   ├── MetaMaskWalletAgent   - EVM chains wallet integration
│   ├── CoinbaseWalletAgent   - CDP Agentic Wallet (primary)
│   ├── EdgeWalletAgent       - Multi-chain self-custody
│   └── AgenticWalletAgent    - Coinbase Agentic Wallet skills
│
├── DAO Agents (2)
│   ├── RealmsDAOAgent        - Solana governance + BTC plugin
│   └── GovernanceToolsAgent  - Multi-chain governance utilities
│
└── Protocol Agents (1)
    └── X402ProtocolAgent     - Machine-to-machine HTTP payments
```

## Supported Blockchains

| Chain | Native Token | Chain ID | Type |
|-------|-------------|----------|------|
| Bitcoin | BTC | N/A | UTXO |
| Ethereum | ETH | 1 | EVM |
| Solana | SOL | N/A | SVM |
| Avalanche | AVAX | 43114 | EVM |
| Base | ETH | 8453 | EVM L2 |
| BNB Smart Chain | BNB | 56 | EVM |
| Polygon | MATIC | 137 | EVM L2 |
| XRP Ledger | XRP | N/A | Custom |

## Supported Tokens

BTC, ETH, SOL, AVAX, AAVE, USDT, USDC, XRP, BNB, XAUT (Tether Gold), UNI

## Key Features

### Coinbase CDP Agentic Wallet
- Autonomous AI wallet on Base network
- Gasless token swaps
- Spending guardrails and KYT screening
- x402 payment protocol support
- Coinbase Onramp for fiat-to-crypto

### x402 Payment Protocol
- HTTP 402-based machine-to-machine payments
- Automatic payment on resource access
- API monetization capabilities
- Session budget management
- Service discovery via x402 bazaar

### DeFi Operations
- Liquidity pool management across 6+ DEXes
- Impermanent loss calculation
- Jupiter aggregator integration (Solana)
- Cross-chain DEX route optimization
- Yield farming strategy support

### DAO Governance (Realms)
- Solana Realms realm creation
- Proposal creation and voting
- Token-weighted governance
- **Mycosoft Labs Bitcoin Plugin:**
  - BTC Ordinals membership NFTs for DAO access
  - Cross-chain voting with Bitcoin proof
  - Bitcoin treasury management via Realms

### Wallet Integrations
- Phantom (Solana)
- MetaMask (EVM chains)
- Coinbase Wallet / CDP
- Edge (Multi-chain)
- Hardware wallet support via MetaMask

## API Endpoints

**Prefix:** `/api/crypto`

### Market Data
- `GET /api/crypto/price/{symbol}` - Token price
- `POST /api/crypto/prices` - Multi-token prices
- `GET /api/crypto/market/overview` - Market overview

### Wallets
- `POST /api/crypto/wallets/create` - Create wallet
- `POST /api/crypto/wallets/agentic` - Create CDP Agentic Wallet
- `GET /api/crypto/wallets` - List wallets
- `GET /api/crypto/wallets/{id}/balance` - Wallet balance

### Transactions
- `POST /api/crypto/send` - Send transaction
- `POST /api/crypto/swap` - Swap tokens
- `GET /api/crypto/gas/{chain}` - Gas estimation

### DeFi
- `POST /api/crypto/defi/liquidity/add` - Add liquidity
- `GET /api/crypto/defi/pools/{chain}` - Get pools
- `GET /api/crypto/defi/raydium/pools` - Raydium pools
- `GET /api/crypto/defi/jupiter/quote` - Jupiter quote
- `GET /api/crypto/defi/dex/route` - Best DEX route

### DAO
- `POST /api/crypto/dao/realms/create` - Create realm
- `POST /api/crypto/dao/proposals` - Create proposal
- `POST /api/crypto/dao/vote` - Cast vote
- `GET /api/crypto/dao/proposals/{id}` - Get proposal

### x402 Payments
- `GET /api/crypto/x402/budget` - Payment budget
- `POST /api/crypto/x402/monetize` - Monetize endpoint
- `GET /api/crypto/x402/services` - Discover services
- `GET /api/crypto/x402/payments` - Payment history

### Chain-Specific
- `GET /api/crypto/btc/fees` - Bitcoin fee estimates
- `GET /api/crypto/btc/block-height` - Block height
- `GET /api/crypto/eth/gas` - Ethereum gas price
- `GET /api/crypto/sol/balance/{address}` - SOL balance
- `GET /api/crypto/stablecoins/peg` - Peg monitoring

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `COINBASE_CDP_API_KEY` | Coinbase CDP API key | For CDP wallet |
| `COINBASE_CDP_API_SECRET` | Coinbase CDP secret | For CDP wallet |
| `ETHEREUM_RPC_URL` | Ethereum RPC endpoint | Optional |
| `SOLANA_RPC_URL` | Solana RPC endpoint | Optional |
| `BITCOIN_RPC_URL` | Bitcoin RPC endpoint | Optional |
| `AVALANCHE_RPC_URL` | Avalanche RPC endpoint | Optional |
| `BASE_RPC_URL` | Base RPC endpoint | Optional |
| `BSC_RPC_URL` | BSC RPC endpoint | Optional |
| `POLYGON_RPC_URL` | Polygon RPC endpoint | Optional |
| `RIPPLE_RPC_URL` | XRP Ledger RPC endpoint | Optional |

## File Structure

```
mycosoft_mas/agents/crypto/
├── __init__.py              # Package exports
├── crypto_base.py           # Base class, chain config, price feeds
├── crypto_coordinator.py    # Master coordinator (22 sub-agents)
├── wallet_manager.py        # Multi-chain wallet management
├── x402_protocol.py         # x402 payment protocol
├── token_agents.py          # 11 token sub-agents
├── defi_agents.py           # LP, Raydium, DEX aggregator
├── wallet_agents.py         # Phantom, MetaMask, Coinbase, Edge
└── dao_agents.py            # Realms, governance tools

mycosoft_mas/core/routers/
└── crypto_api.py            # FastAPI crypto endpoints

tests/
└── test_crypto_agents.py    # 38 unit tests
```

## Integration with Existing MAS

- **MycoDAO Agent:** Shares governance model, extended with on-chain Realms
- **TokenEconomicsAgent:** Token pool management integrated with DeFi
- **IPTokenizationAgent:** Bitcoin Ordinals and Ethereum tokenization
- **FinancialAgent:** Fiat operations complemented by crypto payments
- **FinancialMarketsClient:** CoinGecko/CoinMarketCap data feeds shared

## Agent Registration

All 22 crypto agents + coordinator are registered via:
1. `mycosoft_mas/agents/__init__.py` - Dynamic imports
2. `mycosoft_mas/core/myca_main.py` - Router inclusion
3. POST to `http://192.168.0.188:8001/api/registry/agents` on deploy

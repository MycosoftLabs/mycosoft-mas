# RaaS — Robot-as-a-Service Agent Platform

**Created:** March 11, 2026
**Module:** `mycosoft_mas/raas/`
**Status:** Production-ready backend + middleware

## Overview

The RaaS (Robot-as-a-Service) Agent Platform enables external AI agents from anywhere on the internet to discover, register, pay for, and consume Mycosoft's capabilities. Agents pay via credit card (Stripe) or cryptocurrency (USDC, SOL, ETH, BTC, USDT, AVE) and receive metered access to MYCA's services.

## Architecture

```
External Agent (anywhere on the internet)
    │
    ├── Discovery: GET /.well-known/agent-card.json
    ├── Catalog:   GET /api/raas/services
    ├── Register:  POST /api/raas/agents/register
    ├── Pay:       POST /api/raas/payments/stripe/checkout  (fiat)
    │              POST /api/raas/payments/crypto/invoice    (crypto)
    ├── Invoke:    POST /api/raas/invoke/{service}
    │              ├── /nlm        (10 credits)
    │              ├── /crep       (5 credits)
    │              ├── /earth2     (15-25 credits)
    │              ├── /devices    (5 credits)
    │              ├── /data       (3-5 credits)
    │              ├── /agent      (50 credits)
    │              ├── /memory     (5 credits)
    │              └── /simulation (25 credits)
    └── Account:   GET /api/raas/agents/me
                   GET /api/raas/agents/me/usage
```

## Services Available (8 Categories, 20+ Services)

| Category | Services | Credits/Call |
|----------|----------|-------------|
| NLM Inference | General, species ID, taxonomy, ecology, cultivation, research, genetics | 10 |
| CREP Live Data | Aviation, maritime, satellite, weather | 5 |
| Earth2 Climate | Medium-range forecast, nowcast, spore dispersal, ensemble | 15-25 |
| Device Network | Device list, telemetry, fleet status | 5 |
| MINDEX Data | Species, taxonomy, compounds, knowledge graph | 3-5 |
| Agent Services | Task execution via 158+ agents | 50 |
| Memory & Search | Semantic, fulltext, graph search | 5 |
| Simulations | Petri dish, mycelium, physics | 25 |

## Pricing

### Signup
- **$1 signup fee** (one-time)
- **100 bonus credits** on activation

### Credit Packages

| Package | Credits | Bonus | Total | Price |
|---------|---------|-------|-------|-------|
| Starter | 5,000 | 0 | 5,000 | $5 |
| Growth | 25,000 | 5,000 | 30,000 | $25 |
| Scale | 100,000 | 50,000 | 150,000 | $100 |
| Enterprise | 500,000 | 500,000 | 1,000,000 | $500 |

### Payment Methods
- **Fiat**: Credit card, debit card (via Stripe)
- **Crypto**: USDC, SOL, ETH, BTC, USDT, AVE (via Coinbase exchange rates + Solana RPC verification)

## Authentication

All metered endpoints require `X-API-Key` header:
```
X-API-Key: myca_raas_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

API keys are issued on registration and SHA-256 hashed before storage.

## Money Flow

### Fiat (Stripe)
```
Agent → POST /register → API key issued
Agent → POST /stripe/checkout {package_id: "signup"} → Stripe payment intent
Stripe → POST /stripe/webhook → Agent activated + credits added
Agent → POST /invoke/nlm → Credits deducted, result returned
```

### Crypto
```
Agent → POST /register {payment_method: "crypto"} → API key issued
Agent → POST /crypto/invoice {currency: "USDC"} → Wallet address + amount
Agent → Sends USDC on-chain
Agent → POST /crypto/verify {tx_signature} → Verified via Solana RPC → Credits added
```

## Database Tables (MINDEX 189:5432)

| Table | Purpose |
|-------|---------|
| `raas_agents` | Agent accounts, API keys, status |
| `raas_credits` | Credit balances per agent |
| `raas_credit_transactions` | Credit ledger (purchases, usage, bonuses) |
| `raas_invoices` | Payment invoices (Stripe + crypto) |

## Integration Points

| System | How RaaS Uses It |
|--------|-----------------|
| Economy Store | Records charges and meter events |
| Stripe Client | Creates payment intents |
| Coinbase Client | Exchange rate lookups |
| Solana Client | On-chain transaction verification |
| NLM Service | Inference via `get_nlm_service().predict()` |
| CREP Stream | Redis pub/sub data access |
| Earth2 API | Proxy to internal forecast endpoints |
| Device Registry | Proxy to device/fleet APIs |
| MINDEX Client | PostgreSQL queries for species/taxonomy data |
| Memory System | Semantic and fulltext search |

## Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/raas/__init__.py` | Module init |
| `mycosoft_mas/raas/models.py` | Pydantic models |
| `mycosoft_mas/raas/credits.py` | Credit system (PostgreSQL) |
| `mycosoft_mas/raas/middleware.py` | Auth + credit check dependencies |
| `mycosoft_mas/raas/service_catalog.py` | Service discovery (public) |
| `mycosoft_mas/raas/onboarding.py` | Agent registration |
| `mycosoft_mas/raas/payment_gateway.py` | Stripe + crypto payments |
| `mycosoft_mas/raas/service_proxy.py` | Metered service invocation |
| `mycosoft_mas/raas/agent_card.py` | A2A agent card discovery |
| `mycosoft_mas/raas/mcp_server.py` | MCP server for IDE integration |
| `mycosoft_mas/raas/cli.py` | CLI tool |

## CLI Usage

```bash
# Browse services (no auth)
python -m mycosoft_mas.raas.cli catalog

# Register
python -m mycosoft_mas.raas.cli register --name "MyAgent" --email agent@test.com

# Check balance
python -m mycosoft_mas.raas.cli balance --api-key myca_raas_xxx

# Invoke NLM
python -m mycosoft_mas.raas.cli invoke nlm --query "Identify Amanita muscaria" --api-key myca_raas_xxx

# Invoke CREP
python -m mycosoft_mas.raas.cli invoke crep --data-type weather --api-key myca_raas_xxx
```

## MCP Server

External agents using Claude, Cursor, or MCP-compatible tools:
```bash
python -m mycosoft_mas.raas.mcp_server
```

Provides 8 tools: `raas_catalog`, `raas_register`, `raas_balance`, `raas_packages`, `raas_invoke_nlm`, `raas_invoke_crep`, `raas_invoke_earth2`, `raas_invoke_data`.

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `STRIPE_SECRET_KEY` | Stripe payment processing | For fiat payments |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | For fiat payments |
| `COINBASE_API_KEY` | Exchange rate lookups | For crypto payments |
| `COINBASE_API_SECRET` | Coinbase API auth | For crypto payments |
| `SOLANA_RPC_URL` | Solana transaction verification | For SOL/USDC payments |
| `MYCA_SOL_WALLET` | Mycosoft Solana receiving address | For SOL payments |
| `MYCA_USDC_WALLET` | Mycosoft USDC receiving address | For USDC payments |
| `MYCA_ETH_WALLET` | Mycosoft Ethereum receiving address | For ETH payments |
| `MYCA_BTC_WALLET` | Mycosoft Bitcoin receiving address | For BTC payments |
| `MYCA_USDT_WALLET` | Mycosoft USDT receiving address | For USDT payments |
| `MYCA_AVE_WALLET` | Mycosoft AVE receiving address | For AVE payments |
| `MYCA_RAAS_BASE_URL` | Public-facing URL for agent card | For discovery |

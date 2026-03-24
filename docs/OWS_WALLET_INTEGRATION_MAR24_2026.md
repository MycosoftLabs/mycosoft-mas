# OWS Wallet Integration — March 24, 2026

## Overview

Integration of the **Open Wallet Standard (OWS)** into the MAS, providing every agent with a local-first, multi-chain encrypted wallet. OWS is an open-source protocol by MoonPay, backed by PayPal, Solana Foundation, Ethereum Foundation, Circle, and 21+ organizations.

## Architecture

```
                    ┌─────────────────────────┐
                    │   OWS Wallet API        │
                    │  /api/wallet/ows/*       │
                    │  12 endpoints            │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │   OWSWalletAgent        │
                    │  (BaseAgent v1)          │
                    │  9 task types            │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──┐  ┌───────▼────┐  ┌──────▼──────┐
    │  OWSClient │  │   MINDEX   │  │    Redis     │
    │  (SDK wrap)│  │  PostgreSQL │  │  Event Bus   │
    │  Vault I/O │  │  3 tables  │  │  ows:payments│
    └────────────┘  └────────────┘  └─────────────┘
```

## Supported Chains

| Chain | CAIP-2 ID | Currency |
|-------|-----------|----------|
| Solana | `solana:mainnet` | SOL, USDC |
| Ethereum | `eip155:1` | ETH, USDC |
| Bitcoin | `bip122:000000000019d6689c085ae165831e93` | BTC |
| Tron | `tron:mainnet` | TRX |
| TON | `ton:mainnet` | TON |
| Cosmos | `cosmos:cosmoshub-4` | ATOM |

## Database Schema (MINDEX 189)

- **ows_wallets** — Agent wallet registry (1:1 agent → wallet)
- **ows_transactions** — Append-only transaction ledger
- **ows_balances** — Internal off-chain ledger for instant A2A transfers

## API Endpoints

### Internal (MAS agents)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/wallet/ows/create` | Create wallet for an agent |
| GET | `/api/wallet/ows/{agent_id}` | Get wallet info + balances |
| GET | `/api/wallet/ows/{agent_id}/balance` | Get balance |
| POST | `/api/wallet/ows/transfer` | Internal A2A transfer |
| GET | `/api/wallet/ows/{agent_id}/history` | Transaction history |
| POST | `/api/wallet/ows/sign` | Sign a transaction |
| GET | `/api/wallet/ows/treasury` | MYCA treasury status |

### External (customer agents)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/wallet/ows/onboard` | Create wallet during onboarding |
| POST | `/api/wallet/ows/fund` | Get deposit address |
| GET | `/api/wallet/ows/fund/status/{tx_id}` | Check funding status |
| POST | `/api/wallet/ows/pay` | Pay for API service |

### Worldstate
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/myca/world/economy` | Economy-focused worldview |

## Internal Payment Bus

All internal A2A transfers follow this flow:
1. Agent A calls `/api/wallet/ows/transfer`
2. Debit Agent A's ledger balance
3. Credit Agent B's ledger balance (95%)
4. Credit MYCA treasury (5% fee)
5. Record in `ows_transactions`
6. Publish event to Redis `ows:payments` channel

## Treasury

- Wallet name: `myca-treasury`
- Agent ID: `myca-treasury`
- Receives all API payments, service fees, and 5% internal transfer cut
- Dashboard: `GET /api/wallet/ows/treasury`

## RaaS Integration

Agent registration (`POST /api/raas/agents/register`) now:
1. Creates the `raas_agents` record
2. Provisions an OWS wallet automatically
3. Returns `wallet_name` and `deposit_addresses` in the response
4. New endpoint: `GET /api/raas/agents/{agent_id}/wallet`

## Files

### New
| File | Purpose |
|------|---------|
| `mycosoft_mas/integrations/ows_client.py` | OWS SDK wrapper |
| `mycosoft_mas/agents/crypto/ows_wallet_agent.py` | Wallet management agent |
| `mycosoft_mas/core/routers/ows_wallet_api.py` | Wallet API endpoints |
| `migrations/ows_wallet_tables.sql` | Database schema |
| `tests/test_ows_wallet_agent.py` | Tests |

### Modified
| File | Change |
|------|--------|
| `mycosoft_mas/raas/onboarding.py` | Wallet creation on register |
| `mycosoft_mas/raas/models.py` | Added wallet fields to response |
| `mycosoft_mas/core/routers/worldstate_api.py` | Economy worldview section |
| `mycosoft_mas/core/myca_main.py` | OWS wallet router registration |
| `mycosoft_mas/agents/__init__.py` | OWSWalletAgent import |
| `mycosoft_mas/agents/crypto/__init__.py` | OWSWalletAgent export |
| `mycosoft_mas/core/persistence/economy_store.py` | OWS balance functions |
| `mycosoft_mas/integrations/__init__.py` | OWSClient import |
| `pyproject.toml` | `open-wallet-standard` dependency |

## Deployment

1. Run migration: `psql -h 192.168.0.189 -U mycosoft -d mas -f migrations/ows_wallet_tables.sql`
2. Install SDK on MAS VM: `pip install open-wallet-standard`
3. Create vault directory: `sudo mkdir -p /var/lib/mycosoft/ows-vaults/ && sudo chown mycosoft:mycosoft /var/lib/mycosoft/ows-vaults/`
4. Rebuild and deploy MAS container
5. Initialize treasury: `POST /api/wallet/ows/create` with `agent_id=myca-treasury, wallet_type=treasury`

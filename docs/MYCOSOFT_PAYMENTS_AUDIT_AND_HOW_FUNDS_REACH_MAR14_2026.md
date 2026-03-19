# Mycosoft Payments Audit — How All Forms of Funds Reach Mycosoft

**Date:** March 14, 2026  
**Status:** Audit complete; operator action required (addresses + Square/PayPal)

---

## 1. Executive summary

- **Stripe (cards):** Live. Funds go to your **Stripe account** → payouts to your **connected bank** (Stripe Dashboard).
- **Crypto (USDC, USDT, SOL, ETH, BTC, AVE):** Implemented in MAS RaaS but **cannot receive** until you provide **receive addresses** (see Section 5). **Base USDC** (Coinbase) is not yet wired; added in this pass.
- **x402:** The codebase uses **HTTP 402 Payment Required** when balance is exhausted; there is **no x402 protocol** integration yet. Optional next step.
- **Non-custodial agent USDC:** Supported: agents call MAS `/api/raas/payments/crypto/invoice` (currency=USDC), send USDC to the returned address, then `/crypto/verify` with tx signature. Works once `MYCA_USDC_WALLET` is set.
- **Square and PayPal:** **Not integrated.** Documented below as required configuration; implementation is future work.

---

## 2. Stripe integration (live)

### 2.1 Where it runs

| Surface | Location | Purpose |
|--------|----------|--------|
| **Website** | `website/app/api/stripe/checkout/route.ts`, `lib/stripe/billing.ts` | Subscriptions (Pro/Enterprise), hardware (MycoBrain), PersonaPlex add-on, **agent worldstate** (1-min $1, 60-min $60) |
| **Website webhooks** | `website/app/api/stripe/webhooks/route.ts` | `checkout.session.completed`, subscription and invoice events → update Supabase profiles/orders |
| **MAS RaaS** | `mycosoft_mas/raas/payment_gateway.py` | RaaS signup/credit packages via **payment intents**; webhook at MAS: `POST /api/raas/payments/stripe/webhook` |

### 2.2 How funds reach you (Stripe)

1. Customer/agent pays on **Stripe Checkout** or via RaaS **payment intent**.
2. Stripe holds funds and pays out to your **connected bank account** on the schedule you set in Stripe Dashboard (e.g. daily/weekly).
3. **No USDC or crypto address is used** for Stripe; everything is fiat (cards) → Stripe → bank.

### 2.3 Required Stripe configuration

- **Website:** `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`. Webhook endpoint: `https://mycosoft.com/api/stripe/webhooks` (or sandbox URL).
- **MAS (RaaS):** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` for `https://<MAS_BASE>/api/raas/payments/stripe/webhook`.
- **Rebuild/deploy:** Stripe keys are synced from `.env.local` to the VM by `_rebuild_sandbox.py` so the container has them.

---

## 3. x402 and HTTP 402

- **HTTP 402 Payment Required:** Used when an agent has **insufficient worldstate balance** (e.g. `POST /api/raas/worldstate/start` returns 402). Headers such as `X-Balance-Minutes` indicate balance. This is **not** the x402 payment protocol.
- **x402 protocol:** No x402 (e.g. payment pointers, wallet discovery) is implemented. To support “x402” in the sense of **standardized agent payments**, you would add payment pointer discovery and/or wallet addresses in API responses; the **non-custodial USDC flow** below already allows agents to pay with USDC without custody.

---

## 4. Cryptocurrency and non-custodial agent payments

### 4.1 Implemented (MAS RaaS)

- **Currencies:** SOL, USDC, ETH, BTC, USDT, AVE. **Base USDC** added in code; see Section 6.
- **Flow (non-custodial):**
  1. Agent calls `POST /api/raas/payments/crypto/invoice` with `agent_id`, `package_id`, `currency` (e.g. `USDC`).
  2. MAS returns **your receive address** (`wallet_address`), amount, `invoice_id`, `reference`, `expires_at`.
  3. Agent sends the crypto to that address (e.g. USDC on Solana).
  4. Agent calls `POST /api/raas/payments/crypto/verify` with `invoice_id` and `tx_signature`.
  5. For **SOL and USDC (Solana)** the gateway verifies on-chain and grants credits. For other chains (ETH, BTC, USDT, Base USDC) behavior is either manual verification or chain-specific verification (Base USDC can be added similarly).

### 4.2 Where addresses come from

All receive addresses are **environment variables** on the MAS VM (or wherever RaaS runs). If those env vars are **empty**, crypto invoices return **400** (“No wallet configured for …”). So **you must provide** these addresses (Section 5).

### 4.3 Base USDC (Coinbase)

- **Base** is a separate chain; USDC on Base is distinct from Solana USDC.
- We add **Base USDC** as a supported option and a dedicated env var so you can receive USDC from Coinbase/Base users and agents.

---

## 5. Operator: addresses and config you must provide

**We have not asked for your receive addresses before.** To receive crypto at Mycosoft you must set the following (e.g. in MAS `.env` or VM environment). Use **one wallet per asset/chain** you want to support.

| Env var | Asset / chain | Purpose |
|---------|----------------|--------|
| `MYCA_USDC_WALLET` | USDC (Solana) | Primary USDC for agents; non-custodial agent USDC payments |
| `MYCA_USDC_BASE_WALLET` | USDC (Base) | Base USDC for Coinbase / Base chain |
| `MYCA_USDT_WALLET` | USDT | Tether receive address (specify chain in your wallet: e.g. ERC-20, TRC-20, Solana) |
| `MYCA_ETH_WALLET` | Ethereum | ETH receive address |
| `MYCA_BTC_WALLET` | Bitcoin | BTC receive address |
| `MYCA_SOL_WALLET` | Solana | SOL receive address |
| `MYCA_AVE_WALLET` | AVE | If you use AVE token |

**Action for you:** Send the addresses you want Mycosoft to receive payments to (one per row above). Once set in env and deployed, crypto invoices will return these addresses and agents can pay you directly (non-custodial).

---

## 6. Square and PayPal

- **Square:** Not in the codebase. To accept Square: create a Square application, get credentials, add a payment route (e.g. website or MAS) that creates Square payments and records success; optionally webhooks for payment confirmation.
- **PayPal:** Not in the codebase. To accept PayPal: create a PayPal app, get client ID/secret, add a route that creates PayPal orders and captures payment; optionally webhooks.

Both are **future work**; no addresses or API keys are configured today.

---

## 7. How payments are supposed to work (summary)

| Method | How funds reach Mycosoft | Status |
|--------|---------------------------|--------|
| **Stripe (cards)** | Customer/agent pays → Stripe → your connected bank account | Live (website + RaaS) |
| **USDC (Solana)** | Agent gets invoice with your USDC address → sends USDC → verify with tx → credits | Implemented; needs `MYCA_USDC_WALLET` |
| **Base USDC** | Same idea on Base chain | Added in code; needs `MYCA_USDC_BASE_WALLET` |
| **USDT / ETH / BTC / SOL** | Same invoice/verify flow; your addresses from env | Implemented; needs env set |
| **Non-custodial agent USDC** | Agents send USDC to your address; no custody by Mycosoft | Same as USDC (Solana) once address set |
| **Square** | Would go to your Square account → bank | Not implemented |
| **PayPal** | Would go to your PayPal account → bank | Not implemented |

---

## 8. Files and endpoints reference

- **Website Stripe:** `website/app/api/stripe/checkout/route.ts`, `website/app/api/stripe/webhooks/route.ts`, `website/lib/stripe/billing.ts`, `website/lib/stripe/config.ts`, `website/lib/stripe/server.ts`
- **MAS RaaS payments:** `mycosoft_mas/raas/payment_gateway.py` (Stripe checkout/webhook, crypto invoice/verify, worldstate minutes claim)
- **Worldstate 402:** `mycosoft_mas/raas/worldstate_session.py` (session start/heartbeat return 402 when balance exhausted)
- **Stripe docs:** `website/docs/STRIPE_INTEGRATION.md`

---

## 9. Next steps (operator)

1. **Provide receive addresses** for every asset you want: USDC (Solana), Base USDC, USDT, ETH, BTC, SOL (and AVE if used).
2. **Set env on MAS** (and any other service that uses RaaS): `MYCA_USDC_WALLET`, `MYCA_USDC_BASE_WALLET`, `MYCA_USDT_WALLET`, `MYCA_ETH_WALLET`, `MYCA_BTC_WALLET`, `MYCA_SOL_WALLET`, `MYCA_AVE_WALLET`.
3. **Redeploy MAS** (or restart) so payment_gateway reads the new env.
4. **Optional:** Add Square and PayPal when you are ready (new routes + credentials).
5. **Optional:** Add x402 payment pointer / wallet discovery if you want standards-based agent payment discovery.

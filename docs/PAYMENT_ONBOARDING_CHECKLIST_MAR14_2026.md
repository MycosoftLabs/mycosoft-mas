# Payment Onboarding Checklist — Addresses Mycosoft Needs to Get Paid

**Date:** March 14, 2026  
**Use:** Fill in your receive addresses and set them in MAS (and any deploy) env so Stripe + crypto payments reach you.

---

## You have not been asked for these until now

To receive **crypto** at Mycosoft, the following **environment variables** must be set on the MAS VM (or wherever RaaS runs). Until they are set, crypto invoice endpoints return "No wallet configured" and **you cannot receive** USDC, USDT, BTC, ETH, SOL, or Base USDC.

---

## Required env vars (set on MAS / RaaS host)

Copy into `.env` or VM environment. Replace placeholder with your actual receive address for each asset you want to accept.

```bash
# Solana USDC — primary for non-custodial agent USDC payments
MYCA_USDC_WALLET=

# Base (Coinbase) USDC — for Coinbase / Base chain
MYCA_USDC_BASE_WALLET=

# Tether — specify chain in your wallet (e.g. ERC-20, TRC-20, Solana)
MYCA_USDT_WALLET=

# Ethereum
MYCA_ETH_WALLET=

# Bitcoin
MYCA_BTC_WALLET=

# Solana (SOL)
MYCA_SOL_WALLET=

# AVE (if used)
MYCA_AVE_WALLET=
```

---

## What to send back (operator)

Reply with your **receive addresses** for each asset you want Mycosoft to accept, for example:

| Asset    | Network / chain | Your receive address |
|----------|------------------|-----------------------|
| USDC     | Solana           | …                     |
| USDC     | Base             | …                     |
| USDT     | (e.g. ERC-20)    | …                     |
| ETH      | Ethereum         | …                     |
| BTC      | Bitcoin          | …                     |
| SOL      | Solana           | …                     |

Once set in env and MAS is restarted/redeployed, agents can request crypto invoices and pay you directly (non-custodial).

---

## Fiat (already live)

- **Stripe:** Funds go to your **Stripe account** → payouts to your **connected bank**. Ensure Stripe Dashboard has the correct bank account and payout schedule.
- **Square / PayPal:** Not integrated yet; add when ready.

---

## Full audit

See **MYCOSOFT_PAYMENTS_AUDIT_AND_HOW_FUNDS_REACH_MAR14_2026.md** for how all payment methods work and where funds land.

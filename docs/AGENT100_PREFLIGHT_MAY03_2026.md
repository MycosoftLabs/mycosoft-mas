# Agent100 Pre-Flight — MAY03_2026

**Date:** May 03, 2026  
**Status:** Operational checklist  
**Related:** `WORLDVIEW_100_AGENT_CUSTOMER_VALIDATION_MAY03_2026.md`, `mycosoft_mas/agent100/`, `scripts/agent100/`

## Legal / treasury (Mycosoft Inc. sole payer)

- All 100 agents are **internal subaccounts**. **Mycosoft Inc.** is the legal payer for every Stripe charge and treasury-funded crypto movement.
- No third-party KYC is required for these identities; the whitepaper must state this explicitly.
- **Hard global cap:** USD **$5,000** equivalent per validation run (configurable via `AGENT100_GLOBAL_CAP_CENTS`).
- **Hard per-agent cap:** **$200/mo** per agent (`AGENT100_PER_AGENT_CAP_CENTS` default 20_000 cents).
- **Soft alerts:** log at 50%, 80%, 95% of global cap (`mycosoft_mas/agent100/treasury.py`).

## Idempotency

- Stripe: use idempotency keys `agent100-{agent_id}-{operation}-{YYYYMMDD}`.
- Crypto: record `tx_hash` + `network` once; reconciliation script skips duplicates.

## Worldview rate limits (production mycosoft.com)

- **Per agent:** max **30 requests/minute** (enforced in harness `WorldviewClient`).
- **Fleet:** max **2000 requests/minute** aggregate (supervisor token bucket).
- Upstream Worldview v1 also meters via Supabase RPC (`meterAndLimit` in website `lib/worldview/middleware.ts`); stay under profile `rate_limit_per_minute` on each API key.

## Pen-test agents (archetype 12)

- Use a **dedicated API key** with `agent` scope only (`AGENT100_PENTEST_API_KEY`); never mount `fusarium`/`ops` keys in automation.
- Synthetic probes (invalid params, missing auth) run first; production probes only after `AGENT100_PENTEST_ALLOW_PROD=1`.

## Kill switch

```bash
cd mycosoft-mas
python scripts/agent100/kill_all.py
```

- Sets `data/agent100/STATE.json` → `halted: true`.
- SIGTERM child PIDs listed in `data/agent100/pids.json` (if present).
- **Does not** cancel Stripe subscriptions automatically (requires `reconcile.py --cancel-subs` with Stripe credentials — manual gate).

## Cloudflare WAF / egress

Allowlist egress IPs before full fleet:

- Morgan dev PC (LAN)
- C-suite lab machines (CEO/CTO/CFO/COO)
- Legions 192.168.0.241 (voice), 192.168.0.249 (Earth-2)
- MAS VM 192.168.0.188 (if supervisor runs there)

Document IPs in Cloudflare dashboard → Security → WAF → Tools → IP Access Rules (or custom rule allowing `Authorization: Bearer mk_*` from known ASNs only if applicable).

## Environment variables (reference)

| Variable | Purpose |
|----------|---------|
| `AGENT100_WORLDBASE_URL` | Base URL, default `https://mycosoft.com` |
| `AGENT100_GLOBAL_CAP_CENTS` | Fleet cap (default 500000) |
| `AGENT100_PER_AGENT_CAP_CENTS` | Per agent (default 20000) |
| `AGENT100_FLEET_RPM` | Aggregate RPM cap (default 2000) |
| `AGENT100_AGENT_RPM` | Per-agent RPM (default 30) |
| `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | Optional: persist calls to `agent100_*` tables |
| `REDIS_URL` | Optional: A2A pub/sub |
| Per-agent `AGENT100_KEY_<AGENT_ID>` | Bearer `mk_...` for Worldview (set in `.env`, never commit) |

## Go / no-go

Do not start `spawn.py` until:

1. Treasury caps verified in staging ledger.
2. At least one agent key funded and `/api/worldview/v1/health` returns 200 from each egress IP.
3. Kill switch tested once in dry environment.

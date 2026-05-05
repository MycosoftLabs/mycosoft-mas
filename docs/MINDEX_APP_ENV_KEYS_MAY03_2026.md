# MINDEX App Overhaul — Environment Keys — May 03, 2026

**Status:** Reference only — set values in `.credentials.local` / VM `.env` (never commit secrets).

## Website (`WEBSITE/website/.env.local`)

| Variable | Purpose |
|----------|---------|
| `MINDEX_API_URL` | MINDEX API base (e.g. `http://192.168.0.189:8000`) |
| `NEXT_PUBLIC_MINDEX_API_URL` | Browser-safe MINDEX base URL when needed |
| `MAS_API_URL` | MAS orchestrator for agent actions / pipeline |

## MINDEX API (`MINDEX/mindex/.env`)

| Variable | Purpose |
|----------|---------|
| `SOLANA_RPC_URL` | Solana mainnet RPC (HTTPS) |
| `SOLANA_KEYPAIR_PATH` | Filesystem path to funded keypair JSON (VM only) |
| `SOLANA_NETWORK` | e.g. `mainnet-beta` |
| `BTC_ORDINALS_WALLET` | Ordinals-capable wallet descriptor or address (no WIF in git) |
| `BITCOIN_RPC_URL` | Optional Bitcoin Core RPC when self-hosted |
| `P1_API_KEY` | Platform One production API key |
| `P1_BASE_URL` | Platform One API base URL |
| `NAS_HOST` | e.g. `192.168.0.105` (UniFi NAS) |
| `NAS_SMB_PATH` | Optional UNC hint for operators |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 collectors (IAM-scoped) |
| `AWS_S3_MINDEX_BUCKET` | Primary S3 bucket for federation |
| `PROMETHEUS_PUSHGATEWAY_URL` | Optional pushgateway for MINDEX metrics |
| `PROMETHEUS_METRICS_PATH` | Optional path for scrape textfile exporter |

## MAS (`MAS/mycosoft-mas/.env`)

| Variable | Purpose |
|----------|---------|
| `MINDEX_API_URL` | For agents calling MINDEX |
| `MINDEX_ANCHOR_TIER_THRESHOLDS` | Optional JSON thresholds for anchor_router_agent |
| `FUSARIUM_DEFENSE_ANCHOR_MODE` | When `strict`, bias anchors toward Ordinals tier |

## `.credentials.local` (gitignored)

Add lines **only on secure machines** (no values in repo docs):

- `SOLANA_KEYPAIR_PATH=...`
- `BTC_ORDINALS_WALLET=...`
- `P1_API_KEY=...`
- `AWS_ACCESS_KEY_ID=...` / `AWS_SECRET_ACCESS_KEY=...`

## Verification

```powershell
git grep -n "api_key\s*=\s*['\`"]" MINDEX mindex_api mycosoft_mas WEBSITE/website --glob '!node_modules/**'
```

Any hit must be replaced with `os.environ` / `process.env` patterns per `no-hardcoded-secrets.mdc`.

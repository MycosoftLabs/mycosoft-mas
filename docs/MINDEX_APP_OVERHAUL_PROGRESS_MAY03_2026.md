# MINDEX App Full Overhaul — Progress — May 03, 2026

**Date:** May 03, 2026  
**Status:** In progress (multi-phase; not all plan todos shipped in one session)  
**Related plan:** `.cursor/plans/mindex_app_full_overhaul_may_03_23c797b6.plan.md` (do not edit plan file)

## Delivered this increment

### Website (`WEBSITE/website`)

- `components/natureos/mindex-dashboard.tsx`: `healthAll` state, `fetchHealthAll`, refresh + interval wiring to `OverviewSection`; **nav overhaul** — Bio / Chemistry / Agents tabs; removed Cryptography / separate Phylogeny+Genomics / Containers / Docker strip; voice routes updated; sidebar shows `telemetry_devices` from `health/all`.
- `components/mindex/tabs/mindex-nav-items.ts` + `mindex-dashboard-types.ts`: new `WidgetSection` ids aligned with nav.
- `components/mindex/tabs/bio-tab.tsx`: Tree of life + Genomics sub-tabs (reuses existing sections).
- `components/mindex/tabs/chemistry-tab.tsx`: live compound list via BFF `GET /api/mindex/compounds`.
- `components/mindex/tabs/agents-tab.tsx`: `AdvancedTopology3D` (dynamic, no SSR).
- `components/mindex/tabs/data-pipeline-tab.tsx`: `GET /api/mindex/etl/sources` module list; `TransactionBlockStrip` forced empty (no mock mempool bars).
- `lib/voice/intents.ts`: documented MINDEX voice phrase map for tests / shared classifier.
- `components/mindex/tabs/overview-tab.tsx`: uses `isLoading` for subtle loading affordance; federation card from `/api/mindex/health/all`.
- `.env.local.example`: MAS/MINDEX URLs + BFF auth placeholders (`MINDEX_INTERNAL_TOKEN` / `MINDEX_API_KEY`).
- `app/api/mindex/[[...path]]/route.ts`: catch-all BFF to MINDEX (already present; proxies `health/all`, `ledger/stream`, etc.).
- `lib/mindex-bff-auth.ts`: upstream headers for internal token or API key.

### MINDEX (`MINDEX/mindex`)

- `migrations/0031_mindex_app_overhaul.sql`: ledger, network, devices, synthetic, `core.content_hash`, row-level hashes on taxon/genome/taxon_compound.
- `mindex_api/routers/network.py`: `/network/nodes`, `/network/nodes/{id}`, `/network/edges` (shard join), `/network/devices/live-sensors` (SSE via `telemetry.sample` + `telemetry.stream`), `POST /network/nodes/{id}/refresh` (accept stub).
- `mindex_api/routers/ledger.py`: anchors, DAG, anchor POST, mark-ip, wallet balances, SSE stream (pre-existing / extended in plan).
- `mindex_api/routers/health.py`: `/health/all` aggregate counts.
- `.env.example`: VM-oriented env template for overhaul variables.

### MAS (`MAS/mycosoft-mas`)

- `.env.example` + `infra/mindex-vm/.env.example`: Solana/BTC/P1/NAS/S3/Prometheus/Redis streams / anchor tier threshold placeholders (no secrets).
- `mycosoft_mas/agents/v2/mindex_pipeline_agents.py`: **AnchorRouterAgent**, **DataSynthesisAgent**, **DataQAAgent**, **ChemistrySynthesisAgent**, **DeviceDistributionAgent** — real `httpx` calls to MINDEX + MAS only; tier policy via `MINDEX_ANCHOR_TIER_THRESHOLDS` JSON.
- `mycosoft_mas/agents/v2/__init__.py`: registry keys `anchor-router-agent`, `data-synthesis-agent`, `data-qa-agent`, `chemistry-synthesis-agent`, `device-distribution-agent`.
- `mycosoft_mas/agents/chemistry_synthesis_agent.py`: thin re-export for plan-named module path.
- `mycosoft_mas/agents/device_distribution_agent.py`: thin re-export.
- `n8n/workflows/mindex_full_pipeline_may03.json`, `mindex_anchor_daily.json`, `mindex_device_distribution.json`, `mindex_synthesis_nightly.json`: **inactive** schedule stubs (HTTP probes + code notes); import in n8n UI and wire credentials / MAS task nodes when ready.

## Verification

- `python -c "from mycosoft_mas.agents.v2 import AnchorRouterAgent, ..."` (imports OK).
- Website lint: `mindex-dashboard.tsx`, `overview-tab.tsx` — no new diagnostics in IDE pass.

## Outstanding (follow-on work)

- Apply `0031` on VM **189** and run `python -m mindex_etl.jobs.backfill_content_hash` with production DSN.
- Encyclopedia / species profile / integrity virtualized UI / ledger tab UI / deeper bio tools / devices inventory / mwave / Supabase+Redis+Prom / Playwright / deploy chain / full `MINDEX_APP_OVERHAUL_COMPLETE_*` when all phases done.
- Run **n8n-workflow-sync** after importing the four new JSON workflows on MAS n8n (188).

## How to verify BFF + health/all locally

1. Ensure `MINDEX_API_URL` and `MINDEX_INTERNAL_TOKEN` or `MINDEX_API_KEY` in website `.env.local`.
2. Open NatureOS MINDEX dashboard → Overview; federation card should populate when MINDEX returns `counts`.

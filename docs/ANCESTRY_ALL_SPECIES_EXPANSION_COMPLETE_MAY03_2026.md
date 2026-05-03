# Ancestry All-Species Expansion — MVP Complete (May 03, 2026)

**Date:** May 03, 2026  
**Status:** MVP complete (pagination + kingdom UX + BFF parity)  
**Related plan shell:** `docs/ANCESTRY_ALL_SPECIES_EXPANSION_PLAN_MAY01_2026.md`  
**Architecture context:** `docs/ALL_LIFE_ANCESTRY_EXPANSION_MAY02_2026.md`

## What shipped

| Area | Deliverable |
|------|-------------|
| **Explorer UX** | `/natureos/ancestry/explorer` uses `?kingdom=` synced with desktop Select + mobile Sheet; fungal-first default preserved via dataset tabs (`popular` / `all_species` / `all_taxa`). |
| **Pagination** | Client loads `/api/ancestry?limit=500&sort=…&rank=…&page=N` with optional `kingdom`; **Load more** appends pages until `species.length >= total`. |
| **BFF** | `app/api/ancestry/route.ts` forwards `kingdom` to MINDEX list/search and applies kingdom-aware fallbacks for external APIs where documented. |
| **Kingdom stats** | `app/api/ancestry/kingdoms/route.ts` proxies MINDEX `all-life/kingdom-stats` with empty/error honesty when MINDEX is down. |

## Verification

- Open `/natureos/ancestry/explorer?kingdom=Fungi` (or another kingdom) — URL and UI stay aligned (`router.replace`).
- Network tab: first fetch includes `kingdom` query when not `all`.

## Explicitly deferred

- Cross-kingdom ETL depth beyond existing MINDEX all-life pipelines (see MINDEX `ALL_LIFE_ETL_MAY02_2026`).
- Server-driven infinite scroll / cursor tokens (still page-based MVP).
- n8n orchestration hooks for ancestry-only jobs.

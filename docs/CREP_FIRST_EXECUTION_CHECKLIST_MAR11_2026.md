# CREP-First Execution Checklist

**Date**: March 11, 2026  
**Status**: Plan  
**Related**: CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md, CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md

---

## Overview

This checklist defines the CREP-first implementation wave with concrete repo/file ownership across MAS, MINDEX, WEBSITE, and NatureOS. CREP is the first mandatory rollout surface because it already touches biodiversity, devices, OEI entities, map state, and user interaction.

---

## Phase 2: CREP-First Wave Tasks

### 2.1 Consolidate CREP Entity Model

| Task | Repo | Owner File(s) | Action |
|------|------|---------------|--------|
| Unify entity schema for biodiversity, devices, intelligence | WEBSITE | `lib/crep/entities/unified-entity-schema.ts` | Ensure fungal, device, aircraft, vessel, satellite use one runtime model; extend if needed |
| Use unified schema in CREP unified API | WEBSITE | `app/api/crep/unified/route.ts`, `lib/crep/crep-data-service.ts` | Confirm `getFungalObservations`, devices, aircraft/vessels return `UnifiedEntity` |
| Use unified schema in CREP Dashboard | WEBSITE | `app/dashboard/crep/CREPDashboardClient.tsx` | Verify all overlays consume `UnifiedEntity` |
| Define `analytics report` and `ancestry node` contracts | MAS | `docs/INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md` | Add object definitions for analytics and ancestry (MINDEX phylogeny) |

### 2.2 Local-First Observation Persistence (Clone-on-Display)

| Task | Repo | Owner File(s) | Action |
|------|------|---------------|--------|
| Add clone endpoint to MINDEX | MINDEX | `mindex_api/routers/observations.py` (or new) | Add `POST /api/mindex/observations/clone` (or equivalent) to accept batch from iNaturalist/GBIF; upsert by `source`+`source_id` |
| Implement clone-on-display in CREP fungal | WEBSITE | `app/api/crep/fungal/route.ts` | After returning iNaturalist/GBIF fallback data, fire-and-forget call to MINDEX clone endpoint |
| Verify subsequent reads are MINDEX-local | WEBSITE | `app/api/crep/fungal/route.ts` | Test: first load (fallback) → clone → second load (MINDEX) |
| Document clone flow | MAS | `docs/CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md` | Update checklist; mark clone-on-display complete |

### 2.3 MAS CREP Grounding Upgrade

| Task | Repo | Owner File(s) | Action |
|------|------|---------------|--------|
| Upgrade CREP bridge/sensor layer | MAS | CREP-related routers, device registry, sensor endpoints | Stop reporting status-only summaries; produce entity/state summaries suitable for MYCA context and search evidence |
| Extend Merkle world root for CREP | MAS | `mycosoft_mas/core/routers/merkle_ledger_api.py` | Include CREP entities, biodiversity, sensor state when building `world_root` (when `slot_data` omitted) |
| Define Merkle receipt for CREP entities | MAS / MINDEX | `merkle_ledger_api.py`, `mica.*` schema | Add provenance metadata or Merkle receipt to CREP entity responses without breaking viewport/LOD |

### 2.4 Provenance-Ready Grounding

| Task | Repo | Owner File(s) | Action |
|------|------|---------------|--------|
| Add provenance field to UnifiedEntity | WEBSITE | `lib/crep/entities/unified-entity-schema.ts` | Optional `provenance?: { merkle_receipt?: string; source_id?: string }` |
| Wire CREP fungal response to provenance | WEBSITE | `app/api/crep/fungal/route.ts` | When MINDEX returns observation, include `source`, `source_id`; later add Merkle receipt when available |

---

## Repo/File Ownership Summary

| Repo | Primary Files | Phase 2 Focus |
|------|---------------|---------------|
| **MAS** | `merkle_ledger_api.py`, CREP bridge, device registry | Merkle world root extension; CREP entity summaries; provenance design |
| **MINDEX** | `mindex_api/routers/observations.py`, `mica.*` schema | Clone endpoint; readiness for Merkle writeback |
| **WEBSITE** | `app/api/crep/fungal/route.ts`, `unified-entity-schema.ts`, `CREPDashboardClient.tsx`, `crep-data-service.ts` | Clone-on-display; unified entity usage; provenance fields |
| **NatureOS** | `docs/mycosoft-integration.md` | Doc update (Phase 4); not blocking CREP |

---

## Dependencies

- **Before CREP wave**: Audit complete (CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md)
- **Parallel**: Core platform hardening (retire simulated mindex_query) can proceed; CREP fungal does not use MAS mindex_query
- **After CREP wave**: Search canonical plane, device mapping, analytics, Ancestry, Petri per prioritize-follow-on-surfaces

---

## Verification

1. CREP fungal: first request (MINDEX empty) → iNaturalist fallback → clone fired → second request → MINDEX returns data
2. CREP Dashboard: all entity overlays consume `UnifiedEntity`; no mock data
3. Merkle world root: includes device_registry, device_health, and CREP-relevant slot data when extended
4. No mock/sample data in CREP code paths

# CREP-First System Integration Audit

**Date**: March 11, 2026  
**Status**: Complete  
**Related**: [CREP Merkle Audit Plan](c:\Users\admin2\.cursor\plans\crep_merkle_audit_mar11_3ecab917.plan.md), INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md, FULL_INTEGRATION_READ_WRITE_SEARCH_INTERACT_MAR09_2026.md

---

## Overview

This audit maps every relevant surface across MAS, WEBSITE, MINDEX, and NatureOS to its read/write/search/interact capability and Merkle/MINDEX grounding status. It identifies blocking gaps (mock, stub, simulated paths) and serves as the baseline for the CREP-first execution program.

---

## 1. Surface-by-Surface Audit Matrix

### MAS Surfaces

| Surface | Read | Write | Search | Interact | Merkle/MINDEX Grounding | Gap |
|---------|------|-------|--------|----------|--------------------------|-----|
| **Merkle Ledger API** (`merkle_ledger_api.py`) | ✓ (roots, proofs) | ✓ (event hashes, roots) | — | ✓ (world root build) | World root auto-populates only `device_registry` + `device_health` when `slot_data` omitted; not full live world state | **Partial** – extend to CREP entities, biodiversity, sensor state |
| **MINDEX Query Router** (`mindex_query.py`) | ✗ (simulated) | ✗ (simulated) | ✗ (simulated) | ✗ | **100% simulated** – generates fake telemetry, species, FCI signals, stats | **BLOCKER** – violates no-mock-data; replace with MINDEX bridge |
| **Device Registry API** | ✓ (real) | ✓ (heartbeat) | ✓ (list) | ✓ (command) | Real MAS in-memory + optional MINDEX persistence | None |
| **Investigation API** | ✓ (MINDEX) | ✓ (MINDEX) | ✓ (MINDEX) | ✓ | Calls MINDEX at 189:8000; returns stub when MINDEX unavailable | **Partial** – stub path on MINDEX failure |
| **Identity API** | ✓ (MINDEX) | — | — | — | Uses MINDEX_API_URL | None |
| **LLM Brain** (llm_brain.py) | ✓ (Merkle world root) | — | — | ✓ | Injects Merkle world root into MYCA context | Partial – world root scope limited |

### WEBSITE Surfaces

| Surface | Read | Write | Search | Interact | Merkle/MINDEX Grounding | Gap |
|---------|------|-------|--------|----------|--------------------------|-----|
| **CREP Fungal** (`/api/crep/fungal`) | ✓ (MINDEX primary, iNat/GBIF fallback) | ✗ | ✓ (MINDEX bbox) | ✓ | MINDEX-first; no clone-on-display; no provenance writeback | **Partial** – add clone-on-display |
| **CREP Unified** (`/api/crep/unified`) | ✓ (crep-data-service) | — | — | ✓ | Aggregates fungal, devices, aircraft, vessels, etc.; fungal via getFungalObservations | Uses fungal route; devices from MAS | None |
| **Search Unified** (`/api/search/unified`) | ✓ (MINDEX, iNaturalist, NCBI, PubChem, CrossRef) | ✓ (ingest-background) | ✓ (MINDEX unified-search) | ✓ | MINDEX-first; fire-and-forget background ingestion | None |
| **Devices Network** (`/api/devices/network`) | ✓ (MAS registry) | — | — | ✓ (command POST) | Real MAS; no MINDEX | None |
| **Ancestry Phylogenetic Tree** (`phylogenetic-tree.tsx`) | ✗ (sampleTreeData) | — | — | ✓ | **100% mock** – hardcoded sample tree | **BLOCKER** |
| **Ancestry Phylogeny Page** (`phylogeny/page.tsx`) | ✗ (treeRootMap mock) | — | — | ✓ | Mock tree-root map; PhylogenyVisualization uses rootSpeciesId | **BLOCKER** |
| **CREP Dashboard** | ✓ (unified API) | — | — | ✓ | Consumes unified; no direct MINDEX write | None |

### MINDEX Surfaces

| Surface | Read | Write | Search | Interact | Merkle/MINDEX Grounding | Gap |
|---------|------|-------|--------|----------|--------------------------|-----|
| **Observations API** | ✓ | ✓ | ✓ (bbox, filters) | ✓ | Real obs.observation; taxa lookup | None |
| **Unified Search** | ✓ | — | ✓ | ✓ | Taxa, compounds, genetics | None |
| **mica.* schema** (0021 migration) | ✓ | ✓ | — | ✓ | Merkle ledger; ca_object, event_object, roots | Not yet wired to MAS build paths |

### NatureOS Surfaces

| Surface | Read | Write | Search | Interact | Merkle/MINDEX Grounding | Gap |
|---------|------|-------|--------|----------|--------------------------|-----|
| **Integration docs** (`mycosoft-integration.md`) | — | — | — | — | Documents legacy Azure/Vercel/Cosmos flows | **Drift** – website speaks to MAS/MINDEX VMs directly; doc outdated |
| **Core API** | ✓ | ✓ | — | ✓ | Mushroom1 telemetry, MYCA, HPL | Not canonical for CREP; CREP uses website BFF |

---

## 2. Object Contract Extensions (from INTEGRATION_CONTRACTS_CANONICAL)

| Object | Canonical Source | Status |
|--------|------------------|--------|
| **Search result** | WEBSITE `SpeciesResult`, `CompoundResult`, `GeneticsResult`, `ResearchResult` | Live; MINDEX-first |
| **Analytics report** | Not yet defined | **Missing** – add to contracts |
| **Ancestry node** | MINDEX phylogeny / genetics APIs | **Missing** – Ancestry uses mock; need canonical MINDEX phylogeny API |
| **Simulation outcome** | MAS Petri APIs; MINDEX experiment/session models | **Partial** – Petri UI wiring follow-up per PETRI_DISH_SIM_UPGRADE_TASK_COMPLETE |

---

## 3. Blocking Gaps (First-Class)

| Gap | Location | Severity | Remediation |
|-----|----------|----------|-------------|
| **Simulated MINDEX** | MAS `mindex_query.py` (prefix `/mindex`) | **Critical** | Replace with MINDEX bridge; proxy to 192.168.0.189:8000 or remove and route clients to MINDEX VM |
| **Ancestry sample tree** | `phylogenetic-tree.tsx` – `sampleTreeData` | **Critical** | Remove; fetch from MINDEX phylogeny/taxonomy APIs |
| **Ancestry mock tree-root map** | `phylogeny/page.tsx` – `treeRootMap` | **Critical** | Replace with MINDEX taxonomy/order-level roots |
| **World root partial** | `merkle_ledger_api.py` – `build_world_root_endpoint` | **High** | Extend slot_data to include CREP entities, biodiversity, sensor state |
| **Clone-on-display missing** | CREP fungal route | **High** | Implement per CREP_INATURALIST_MINDEX_ETL; POST to MINDEX on iNaturalist/GBIF fallback |
| **Provenance writeback** | CREP entities | **Medium** | Add Merkle receipt or metadata to CREP entity responses |
| **Investigation stub on MINDEX fail** | `investigation_api.py` | **Medium** | Fail explicitly; never return fake investigations |
| **NatureOS doc drift** | `mycosoft-integration.md` | **Low** | Update to current VM layout and MAS/MINDEX direct integration |

---

## 4. Canonical Flow (Enforced)

```
Devices + MycoBrain → MAS Runtime
CREP + App Surfaces → MAS Runtime
MAS → MINDEX Truth Plane
MINDEX → Unified Search
MAS → Merkle Grounding
MINDEX → Merkle (mica.* schema)
Merkle → CREP, Search, NatureOS, Petri, Analytics
```

---

## 5. Summary by Repo

| Repo | Read | Write | Search | Merkle | Blockers |
|------|------|-------|--------|--------|----------|
| **MAS** | Partial (mindex_query simulated) | Partial | Simulated | Partial (world root limited) | mindex_query 100% simulated |
| **WEBSITE** | Good (CREP, Search MINDEX-first) | Partial (ingest-background) | Good | None | Ancestry mock |
| **MINDEX** | Good | Good | Good | Schema ready (mica.*) | Not connected to MAS Merkle build |
| **NatureOS** | Good | Good | — | — | Doc drift |

---

## 6. References

- `docs/INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md`
- `docs/FULL_INTEGRATION_READ_WRITE_SEARCH_INTERACT_MAR09_2026.md`
- `docs/MICA_MERKLE_LEDGER_INTEGRATION_MAR09_2026.md`
- `docs/CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md`
- `docs/CREP_SPECIES_WIDGETS_VIEWPORT_LOADING_COMPLETE_MAR11_2026.md`
- `MINDEX/migrations/0021_mica_merkle_ledger.sql`
- `mycosoft_mas/core/routers/mindex_query.py`
- `mycosoft_mas/core/routers/merkle_ledger_api.py`
- `WEBSITE/app/api/crep/fungal/route.ts`
- `WEBSITE/app/api/search/unified/route.ts`
- `WEBSITE/components/ancestry/phylogenetic-tree.tsx`
- `WEBSITE/app/ancestry/phylogeny/page.tsx`

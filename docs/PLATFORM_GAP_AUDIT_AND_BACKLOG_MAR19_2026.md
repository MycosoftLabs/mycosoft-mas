# Platform Gap Audit and Backlog — Mar 19, 2026

**Date:** March 19, 2026  
**Status:** Master backlog (live)  
**Related:** [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md), [EXECUTION_WAVES_AND_ACCEPTANCE_MAR19_2026.md](EXECUTION_WAVES_AND_ACCEPTANCE_MAR19_2026.md), [DOC_DRIFT_AND_INDEX_TRIAGE_MAR19_2026.md](DOC_DRIFT_AND_INDEX_TRIAGE_MAR19_2026.md)

---

## Executive summary

This document is the **single entry point** for cross-repo platform gaps, unfinished work, and integration holes. It links to machine-generated backlog (`gap_report_latest.json`), human-authored execution reports, and the phased build roadmap (P0–P3 waves).

**Summary counts (from last gap scan):**
- TODOs/FIXMEs: 639 (noisy; many false positives in bundled/debug code)
- Stubs: 298 (structural; many intentional base-class patterns)
- 501 routes: 199 (needs reconciliation with actual website routes—likely inflated)
- Index-level gaps: 180 across 34 files (`cursor_index_scan`)

**Principle:** Do not re-invent full CREP, search, or worldview plans. **Link** existing docs and track only open checkboxes and actionable items.

---

## Machine backlog sources

| Source | Location | How to refresh |
|--------|----------|----------------|
| **Gap report JSON** | `.cursor/gap_report_latest.json` | `python scripts/gap_scan_cursor_background.py` (every 15–30 min) or MAS `GET /agents/gap/scan` |
| **cursor_index_scan** | Inside gap report, `index_gaps.referenced_files_with_gaps` | Same as above; ~180 unchecked/todo/stub items across 34 files |
| **MAS gap API** | `GET http://192.168.0.188:8001/agents/gap/scan` | Run when MAS is up; returns full scan result |

---

## P0–P3 waves (dependency order)

```
P0 (Security) → P1 (Contracts/BFF) → P2 (Voice/Realtime)
                                    → P3 (Data plane / UI)
```

| Wave | Scope | Blocking? |
|------|-------|-----------|
| **P0** | Security (credentials, base64 audit, mock-data removal) | Blocks where cited |
| **P1** | Integration contracts (BFF, MAS↔MINDEX, CREP command, 501 reconciliation) | Blocks P2/P3 |
| **P2** | Voice E2E, WebSocket/SSE spine, GPU placement docs | — |
| **P3** | Scientific dashboards data, NatureOS/superapp wiring, MYCA2 verification | — |

---

## Canonical reference docs (do not duplicate)

| Doc | Purpose |
|-----|---------|
| [GAPS_AND_SECURITY_AUDIT_MAR14_2026.md](GAPS_AND_SECURITY_AUDIT_MAR14_2026.md) | Security items and implementation gaps; completion notes |
| [CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md](CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md) | Surface-by-surface CREP integration matrix |
| [CREP_COMMAND_CONTRACT_MAR13_2026.md](CREP_COMMAND_CONTRACT_MAR13_2026.md) | CREP map command schema |
| [SYSTEM_EXECUTION_REPORT_FEB09_2026.md](SYSTEM_EXECUTION_REPORT_FEB09_2026.md) | Deploy/Cloudflare/MAS/website status |
| [SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md](SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md) | NatureOS/superapp unification plan |

---

## Non-goals

- Fix every TODO without triage (many are noise in bundled/vendored code).
- Rewrite full CREP ETL or entire search platform—only add **connection** tasks where missing.

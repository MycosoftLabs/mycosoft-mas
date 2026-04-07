# Deferred Gap Items — Go / No-Go — April 6, 2026

**Date:** April 6, 2026  
**Status:** Decision record (recommended defaults)  
**Sources:** `docs/GAP_PLAN_COMPLETION_MAR05_2026.md`, `docs/GAP_PLAN_LARGE_SCAFFOLDING_MAR05_2026.md`, `docs/NEXT_JOBS_FROM_GAPS_MAR07_2026.md`

---

## Medium deferrals (Mar 5)

| Item | Recommendation | Rationale |
|------|----------------|-----------|
| **Staff/task context API** | **GO — Q3** | High value for MYCA relevance; blocked on picking **one** system of record (Asana vs GitHub Projects vs Linear). Schedule after credential + scope decision. |
| **Mycorrhizae → MYCA telemetry bridge** | **GO — phased** | Start with read-only telemetry from Mycorrhizae API into MAS context injection; full bidirectional later. |
| **Morgan approval UX** | **GO — incremental** | Ship small: inline approve/reject on existing confirmation surfaces before a full redesign. |

---

## Large architectural six-pack (Jobs 18–23)

| Job | Recommendation | Rationale |
|-----|----------------|-----------|
| **18 Full Morgan control plane** | **GO — after** oversight panel hardening | Depends on stable autonomous loop metrics. |
| **19 MYCA worldview digest** | **GO** | Aligns with RAG + EP summary already partially in place; compose digest in MAS pre-turn. |
| **20 Unified front door** | **GO — long** | Requires Cowork + Cursor contract; single webhook ingress to MYCA first, then delegate. |
| **21 NatureOS → MYCA event bridge** | **GO** | Webhook MVP (`POST` to MAS) before SignalR subscription complexity. |
| **22 MycoBrain situational awareness** | **GO** | Builds on device registry + telemetry; narrow MVP: “devices + last reading summary.” |
| **23 Unified workflow visibility** | **GO** | Read-only aggregate from n8n APIs on 188 + 191; no new n8n cluster required for v1. |

**None marked NO-GO** — all deferred for sequencing and capacity, not rejection.

---

## Owner

Product priority remains with Morgan; engineering should pull from this list in Tier 2–4 order from `docs/GAP_SCAN_RECONCILIATION_APR06_2026.md` companion backlog narrative.

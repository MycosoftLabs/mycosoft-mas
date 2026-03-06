# Next Jobs from Gaps — March 7, 2026

**Date:** March 7, 2026  
**Status:** Living document  
**Purpose:** Prioritized job list derived from gap docs — what NEEDS to be done next

**Sources:**
- `docs/MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md`
- `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`
- `docs/SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md`

---

## Executive Summary

This plan merges platform status, MYCA upgrade audit, and system gaps into a single **prioritized job list**. Jobs are ordered by impact and urgency: **Critical first**, then **High**, then **Quick wins**, then **Medium**, then **Large**.

---

## 1. Critical (Do First)

| # | Job | Repo | Est. | Notes |
|---|-----|------|------|-------|
| 1 | **Replace base64 with AES-GCM** | MAS | 1 day | `mycosoft_mas/security/security_integration.py` — security flaw; rotate any exposed secrets |
| 2 | **Implement 501 API routes** | MAS, WEBSITE | 2–3 days | `/api/mindex/wifisense`, `/api/mindex/agents/anomalies`, `/api/docker/containers`, and other 501s — replace with real logic or proper 404/503 |

---

## 2. High Priority

| # | Job | Repo | Est. | Notes |
|---|-----|------|------|-------|
| 3 | **Add missing website pages** | WEBSITE | 2 days | `/contact`, `/support`, `/careers`, `/myca`, `/auth/reset-password`, `/dashboard/devices` — create or redirect |
| 4 | **Replace stub implementations** | MAS, MINDEX | 3–5 days | Financial agents (Mercury, QuickBooks, Pulley), Research agent handlers, Task Manager, mem0_adapter, WiFiSense/anomalies backends |
| 5 | **Voice system completion** | MAS, WEBSITE | ~40% done | Finish test-voice, PersonaPlex integration, MYCA voice flow per `docs/VOICE_*` |

---

## 3. Quick Wins (1–2 days each)

| # | Job | Repo | Impact |
|---|-----|------|--------|
| 6 | MYCA state widget on dashboard | WEBSITE | Morgan sees consciousness, grounding, pending confirmations |
| 7 | Document A2A agent for MYCA | MINDEX, MAS | Clear delegation path for search/stats |
| 8 | Document Cowork vs MYCA scope | MAS | Reduces duplication and confusion |
| 9 | Document MycoBrain→MAS flow | MAS, mycobrain | MYCA can query device registry |
| 10 | Pass page context to MYCA | WEBSITE | "Morgan is on CREP" improves replies |

---

## 4. Medium Upgrades (3–7 days each)

| # | Job | Repo | Impact |
|---|-----|------|--------|
| 11 | Morgan oversight panel | WEBSITE | Single control/visibility surface |
| 12 | Staff/task context API | MINDEX or MAS | MYCA knows "what is Morgan working on?" |
| 13 | EP summary endpoint | MINDEX | MYCA gets recent experience packet summary |
| 14 | NatureOS summary endpoint | NatureOS | MYCA can "summarize NatureOS state" |
| 15 | Mycorrhizae→MYCA telemetry bridge | MAS | MYCA sees lab telemetry when relevant |
| 16 | MYCA→n8n trigger pattern | MAS, n8n | Standard "MYCA triggers workflow" path |
| 17 | Morgan approval UX in MYCA | WEBSITE | Smoother approve/reject for autonomous actions |

---

## 5. Large / Architectural (2+ weeks each)

| # | Job | Dependencies | Impact |
|---|-----|--------------|--------|
| 18 | Full Morgan control plane | Oversight panel, workflow visibility | Supervise, steer, trust MYCA |
| 19 | MYCA worldview digest | KG, memory, EP | MYCA maintains rich context |
| 20 | Unified front door | Cowork webhooks, Cursor context | Morgan stays in MYCA; MYCA delegates |
| 21 | NatureOS→MYCA event bridge | SignalR or webhook | Device alerts → MYCA context |
| 22 | MycoBrain situational awareness | Telemetry bridge, device status | MYCA "sees" lab state |
| 23 | Unified workflow visibility | Both n8n instances | "What ran for Morgan" in one view |

---

## 6. Recommended Sprint Order

### Sprint 1 (This week)
1. **#1** — Security: base64 → AES-GCM
2. **#6** — MYCA state widget
3. **#10** — Pass page context to MYCA

### Sprint 2 (Next week)
4. **#2** — Implement 501 routes (or triage to 404/503)
5. **#7, #8, #9** — Documentation (A2A, Cowork vs MYCA, MycoBrain→MAS)
6. **#3** — Add missing pages (contact, support, careers, myca)

### Sprint 3 (Following)
7. **#11** — Morgan oversight panel
8. **#12** — Staff/task context API (if Asana/GitHub integration exists)
9. **#16** — MYCA→n8n trigger pattern

---

## 7. Cross-References

| Doc | Purpose |
|-----|---------|
| `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md` | Full upgrade audit with verification checklist |
| `docs/SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md` | Gap scan, TODOs, stubs, 501 routes |
| `docs/MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md` | Platform status, VM layout, next steps |
| `.cursor/gap_report_latest.json` | Latest gap scan (run `python scripts/gap_scan_cursor_background.py`) |

---

## 8. Verification

- [x] Security: base64 removed; AES-GCM in place (verified Mar 5, 2026)
- [x] No 501 routes without real implementation or proper error (verified)
- [x] Missing pages exist or redirect (verified)
- [x] MYCA state visible on dashboard
- [x] Page context passed to MYCA
- [x] A2A, Cowork vs MYCA, MycoBrain→MAS documented
- [x] Morgan oversight panel exists
- [ ] Staff/task context API available (deferred — requires Asana/GitHub)
- [x] MYCA→n8n trigger pattern documented and used
- [x] NatureOS summary endpoint created (`/api/natureos/summary`)

# External Repository Integration — Gap Alignment

**Date**: March 10, 2026  
**Status**: Complete

## Overview

Cross-check of the external-repo integration roadmap against current indexed platform gaps. Ensures new work strengthens the architecture instead of increasing drift.

**Sources**: `.cursor/gap_report_index.json`, `.cursor/gap_report_latest.json`

---

## Current Gap Summary

| Metric | Value |
|--------|-------|
| Files with gaps | 34 |
| Indexed gap items | ~180 |
| Files checked | 157 |
| Referenced paths | 185 |

---

## High-Impact Debt (Before Adding External Repos)

### 1. Grounded Cognition

- **SpatialService, TemporalService** — Stubs only; PostGIS/TimescaleDB integration planned.
- **Phase 2–4 unchecked items** — Grounding status, EP endpoints, ThoughtObjectsPanel, settings toggle, verification steps.
- **Relevance to external repos**: LocalAI/llmfit do not touch grounded cognition. **No conflict.**

### 2. Search Endpoint Gaps

- **TODO**: Create `/api/mindex/research/search` — currently uses `/api/mindex/research?search=...`.
- **Relevance**: Turf/Leaflet (geo stack) supports CREP search visualization; does not replace MINDEX search. **No conflict.** Action-label-syncer is governance-only. **No conflict.**

### 3. NatureOS Placeholder Removal

- **NatureOS upgrade prep** — 17+ unchecked items: mock data removal, compatibility routes, real-time updates, MYCA context.
- **FungaService stubs** — Lab tools, experiments placeholder.
- **Relevance**: External repos do not add NatureOS code. Finance plugins stay in MAS/C-suite. **No conflict.**

### 4. Documentation Drift

- **CURSOR_DOCS_INDEX** — Work streams, vision gaps, agents/rules references.
- **MASTER_DOCUMENT_INDEX** — Stub/TODO references.
- **Relevance**: External-repo docs are additive. **No conflict.**

### 5. Stub and Placeholder Debt

- **STUB_IMPLEMENTATIONS_FEB12_2026** — Agent lifecycle, anomaly querying, Clerky API, NAS write, etc.
- **Relevance**: LocalAI, llmfit, tirith, shannon are new prototypes, not replacements for existing stubs. **No conflict** if kept isolated.

---

## Stream-by-Stream Gap Alignment

### Stream 1: Geo and CREP Standardization (Turf, Leaflet)

| Gap | Alignment |
|-----|-----------|
| CREP LOD / iNaturalist ETL | Turf supports bbox, clustering, geometry math; **strengthens** CREP local-first path. |
| Search endpoint (`/api/mindex/research/search`) | Geo stack is visualization/preprocessing; does not add or replace search. **Neutral.** |
| Grounded cognition spatial stub | PostGIS is separate; Turf is client/API-side. **No overlap.** |

**Verdict**: Proceed. Strengthens CREP; does not worsen existing gaps.

---

### Stream 2: Local Inference (LocalAI, llmfit)

| Gap | Alignment |
|-----|-----------|
| Voice/PersonaPlex topology | LocalAI as MAS provider fallback; must not replace Ollama/PersonaPlex. **Controlled prototype only.** |
| Grounded cognition | No overlap. |
| Stub implementations | LocalAI is new capability; not replacing stubs. **Neutral.** |

**Verdict**: Proceed as controlled prototype. Block if it destabilizes voice or duplicates Ollama without clear replacement value.

---

### Stream 3: Governance and Finance (action-label-syncer, financial-services-plugins)

| Gap | Alignment |
|-----|-----------|
| Documentation drift | Label syncer improves repo hygiene. **Strengthens.** |
| CFO MCP connector | Financial plugins map onto existing CFO surfaces. **Strengthens.** |
| Platform-wide stubs | Finance patterns stay in MAS/C-suite; no WEBSITE runtime. **No conflict.** |

**Verdict**: Proceed. Low risk; improves governance.

---

### Stream 4: Security and Operational Guardrails (tirith, shannon, benchmark-action)

| Gap | Alignment |
|-----|-----------|
| Security TODOs (SECURITY_BUGFIXES_FEB09_2026) | tirith, shannon support pentest/validation. **Strengthens** security posture. |
| Shell/agent safety | tirith addresses command safety in Cursor/MYCA workflows. **Strengthens.** |
| Benchmark-action | Add only after defining benchmark suite. **Block until** MAS latency, MINDEX queries, CREP transforms have clear benchmarks. |

**Verdict**: Proceed with tirith, shannon. **Block** benchmark-action until benchmark suite is defined.

---

### Stream 5: Repo and Design Hygiene (Uncodixfy, action-label-syncer)

| Gap | Alignment |
|-----|-----------|
| Documentation / rules | Uncodixfy as Cursor rules improves design quality. **Strengthens.** |
| Label syncer | Covered in Stream 3. **No conflict.** |

**Verdict**: Proceed.

---

## Blocking Rules for Prototypes

Any prototype must be **blocked** if it:

1. **Duplicates an existing runtime** (e.g., second orchestration plane, second map stack) without explicit replacement value.
2. **Touches unfinished grounded cognition paths** (SpatialService, TemporalService, EP storage) in a way that increases stub count.
3. **Adds WEBSITE runtime code** for features that should live in MAS or MINDEX (e.g., finance plugins in WEBSITE).
4. **Introduces scraping/anti-bot tooling** (nodriver, cloudscraper) — explicitly excluded.
5. **Increases documentation drift** — new docs must be added to MASTER_DOCUMENT_INDEX and kept current.

---

## Recommended Sequencing Given Gaps

1. **Low-risk first**: action-label-syncer, Uncodixfy-derived Cursor guidance. No gap impact.
2. **Geo stack**: Turf + Leaflet. Supports CREP; does not block or worsen grounded cognition or search.
3. **Local inference prototype**: llmfit + LocalAI. Keep behind MAS provider; do not destabilize voice.
4. **Security/ops**: tirith, shannon. Run only in non-production; defer benchmark-action until suite exists.
5. **Finance specialization**: Extract patterns; keep in MAS/C-suite.
6. **Watchlist** (Prefect, plotly.py, vinext, ctop): Revisit only after reducing current platform gaps (e.g., stub replacements, search endpoint, NatureOS placeholder removal).

---

## Related Documents

- [External Repo Classification](./EXTERNAL_REPO_CLASSIFICATION_MAR10_2026.md)
- [External Repo System Boundaries](./EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md)
- [External Repo Implementation Streams](./EXTERNAL_REPO_IMPLEMENTATION_STREAMS_MAR10_2026.md)
- [Gap Plan Completion](./GAP_PLAN_COMPLETION_MAR05_2026.md)

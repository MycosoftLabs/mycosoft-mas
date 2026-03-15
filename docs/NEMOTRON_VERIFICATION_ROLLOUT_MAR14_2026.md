# Nemotron MYCA/AVANI Verification and Rollout

**Date:** March 14, 2026  
**Status:** Reference (test gates, rollout sequence, doc/registry updates)  
**Related:** `nemotron_myca_rollout_8469ab79.plan.md` §7, NEMOTRON_DEPLOYMENT_TOPOLOGY_MAR14_2026.md, SPEECH_DUPLEX_MIGRATION_MAR14_2026.md, MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.md

---

## 1. End-to-End Test Gates

### 1.1 Canonical voice path (bridge → brain)

- **Gate:** One end-to-end flow: browser mic → PersonaPlex bridge → MYCA Nemotron brain → AVANI verdict → interruptible speech output → persisted memory/context.
- **Steps:**
  1. Start bridge (8999) and MAS (8001); ensure Brain API and AVANI evaluate are reachable.
  2. Open `/test-voice`; establish session; speak; confirm response is generated via MAS brain (not a bypass).
  3. Trigger barge-in (speak while MYCA is talking); confirm interruption and new turn.
  4. Confirm session/context is persisted (e.g. memory or grounding packet stored).
- **Pass:** Full path exercised; no fallback that bypasses brain or AVANI for voice.

### 1.2 Route unification and governance

- **Gate:** All MYCA ingress routes (chat, search/chat, voice proxy) call the same backend contract; AVANI cannot be bypassed.
- **Steps:**
  1. Call `/api/chat` and `/api/search/chat` with a message that would trigger AVANI block; confirm block is applied.
  2. Confirm no website-only path that skips `POST /api/avani/evaluate-message` (or equivalent backend).
  3. Verify Brain API and any Nemotron-backed endpoint apply AVANI before executing.
- **Pass:** No ingress path bypasses backend AVANI.

### 1.3 Retrieval provenance and RAG

- **Gate:** MINDEX retrieval used by MYCA (live-context, memory brain, world-model) returns provenance-rich results; no parallel “Nemotron worldview” contract—use canonical WorldState/WorldStateRef.
- **Steps:**
  1. Trigger a query that uses RAG (e.g. search or brain with context); inspect response metadata for source IDs, collection, timestamps.
  2. Confirm WorldModel/grounding uses same retrieval path as documented in GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026 and MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.
- **Pass:** Single retrieval contract; provenance present; aligned with WorldState.

### 1.4 Full-duplex interruption behavior

- **Gate:** Regression tests for barge-in, VAD state, and session continuity after interrupt.
- **Steps:**
  1. Automated or manual: start voice session, send TTS request, send interrupt before completion; confirm TTS stops and new request can start.
  2. Confirm DuplexSession (or equivalent) state is consistent (no stuck “speaking” state).
- **Pass:** Interrupt is honored; session recovers for next turn.

---

## 2. Rollout Sequencing

| Phase | Scope | Dependency | Verification |
|-------|--------|------------|--------------|
| **1** | Canonical voice path (bridge → brain only); no Nemotron model yet | PersonaPlex + MAS brain + AVANI backend | Gate 1.1, 1.2 |
| **2** | Unified LLM routing (Nemotron-capable); Nemotron core on 188 or 190 | config/models.yaml, LLMRouter/FrontierLLMRouter/LLMBrain | Brain responses use unified router; no split-brain |
| **3** | AVANI authoritative backend; all ingress routes gated | AVANI evaluate endpoint; website routes proxy | Gate 1.2 |
| **4** | MINDEX RAG (embedding + rerank + provenance); worldstate-grounded retrieval | MINDEX API, WorldModel, mindex_bridge | Gate 1.3 |
| **5** | Speech migration (optional Phase 2): backend ASR/TTS with interrupt | SPEECH_DUPLEX_MIGRATION_MAR14_2026; bridge pluggable STT/TTS | Gate 1.4; /test-voice parity |
| **6** | Deployment topology: services on 187/188/189/190 + NAS model storage | NEMOTRON_DEPLOYMENT_TOPOLOGY_MAR14_2026 | Health checks; no duplicate authority |

Rollout order: 1 → 2 → 3 (can overlap with 4). Then 4; then 5 when speech backend is ready; 6 is ongoing ops alignment.

---

## 3. Required Doc and Registry Updates

### 3.1 Documentation

- **Created this rollout:**
  - `docs/NEMOTRON_VERIFICATION_ROLLOUT_MAR14_2026.md` (this file)
  - `docs/NEMOTRON_DEPLOYMENT_TOPOLOGY_MAR14_2026.md`
  - `docs/SPEECH_DUPLEX_MIGRATION_MAR14_2026.md`
  - `docs/MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.md`
- **Keep updated:** GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md, WORLDSTATE_CONTRACT_MAR14_2026.md, WORLDSTATE_VS_SPECIALIST_COMMAND_BOUNDARY_MAR14_2026.md when retrieval or worldstate contracts change.
- **Index:** Add all Nemotron/AVANI rollout docs to `docs/MASTER_DOCUMENT_INDEX.md`; add vital ones to `.cursor/CURSOR_DOCS_INDEX.md` if they are primary references for agents.

### 3.2 Registries

- **System Registry (`docs/SYSTEM_REGISTRY_FEB04_2026.md`):**
  - Add or update entries for: Nemotron inference service(s), AVANI backend service, Nemotron speech (ASR/TTS) when deployed, RAG/retrieval service on MINDEX.
  - Update VM/service table for 187/188/189/190 and NAS model storage roles per NEMOTRON_DEPLOYMENT_TOPOLOGY_MAR14_2026.md.
- **API Catalog (`docs/API_CATALOG_FEB04_2026.md`):**
  - Document any new endpoints: e.g. AVANI evaluate-message (if not already), Nemotron brain/chat endpoints, RAG/retrieve if exposed as a dedicated API.
- **Voice topology:** Update voice/PersonaPlex docs to state that bridge → MAS brain is the single canonical realtime path and list any new speech service URLs (e.g. Nemotron ASR/TTS on 190).

### 3.3 Ops runbooks

- When Nemotron core, speech, or RAG are deployed on VMs: document startup order, health URLs, and NAS mount paths in ops runbooks (no secrets in docs; use env vars).

---

## 4. Completion Checklist (per plan §7)

- [ ] One canonical end-to-end flow proven (browser mic → bridge → brain → AVANI → speech → memory).
- [ ] Regression tests added/run for route unification, governance enforcement, retrieval provenance, full-duplex interruption.
- [ ] Docs updated: MASTER_DOCUMENT_INDEX, CURSOR_DOCS_INDEX (vital only), grounding/worldstate docs if contracts changed.
- [ ] Registries updated: SYSTEM_REGISTRY (inference services, AVANI backend, speech, RAG), API_CATALOG (new endpoints), voice topology.
- [ ] Deployment topology and ops runbooks aligned with actual service placement (187/188/189/190, NAS).

---

**Next:** Execute rollout phases in order; run test gates after each phase; update checklists and registries when implementation is complete.

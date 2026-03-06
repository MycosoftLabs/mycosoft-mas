# Gap Plan Large Items — Scaffolding (March 5, 2026)

**Date:** March 5, 2026  
**Status:** Scaffolding — Design placeholders for future sprints  
**Related:** `docs/NEXT_JOBS_FROM_GAPS_MAR07_2026.md`, `docs/GAP_PLAN_COMPLETION_MAR05_2026.md`

---

## Purpose

This document provides scaffolding (design stubs, dependencies, and acceptance criteria) for the 6 Large/Architectural items from the gap plan. Implementation is deferred to future sprints.

---

## 1. Full Morgan Control Plane (Job #18)

**Dependencies:** Morgan oversight panel (done), workflow visibility  
**Impact:** Supervise, steer, trust MYCA  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** Extend `app/dashboard/morgan/page.tsx` with control surfaces
- **Capabilities:** Approve/reject pending confirmations, pause/resume MYCA autonomous loop, view task queue, override decisions
- **API:** `GET/POST /api/myca/control` or MAS orchestrator control endpoints
- **Acceptance:** Morgan can pause autonomous work, approve high-risk actions, view queue

---

## 2. MYCA Worldview Digest (Job #19)

**Dependencies:** KG, memory, EP summary (done)  
**Impact:** MYCA maintains rich context before each turn  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** MAS memory/grounding pipeline; MINDEX EP summary (done)
- **Capabilities:** Pre-turn context injection: recent EP summary, KG facts, memory highlights
- **API:** Extend MINDEX grounding; MAS orchestrator context assembly
- **Acceptance:** MYCA receives digest before replying; context window used efficiently

---

## 3. Unified Front Door (Job #20)

**Dependencies:** Cowork webhooks, Cursor context  
**Impact:** Morgan stays in MYCA; MYCA delegates to Cowork/Cursor  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** MYCA webhooks, Cowork ingest, Cursor MCP
- **Capabilities:** External requests (Cowork, Cursor) → MYCA; MYCA delegates back to tools
- **Docs:** `COWORK_VS_MYCA_SCOPE_MAR07_2026.md` (done)
- **Acceptance:** Single entry point; MYCA routes and delegates

---

## 4. NatureOS→MYCA Event Bridge (Job #21)

**Dependencies:** SignalR or webhook  
**Impact:** Device alerts → MYCA context  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** NatureOS hub/webhook; MAS ingest
- **Capabilities:** Device events (alerts, state changes) → MYCA context
- **API:** Webhook `POST /api/webhooks/natureos/events` or SignalR subscription
- **Acceptance:** MYCA receives NatureOS device events when relevant

---

## 5. MycoBrain Situational Awareness (Job #22)

**Dependencies:** Telemetry bridge, device status  
**Impact:** MYCA "sees" lab state  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** MycoBrain service → MAS; MYCA context
- **Docs:** `MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md` (done); `MYCORRHIZAE_MYCA_TELEMETRY_BRIDGE_MAR07_2026.md` (design)
- **Capabilities:** Lab telemetry, device status, environmental data in MYCA context
- **Acceptance:** MYCA can answer "what's happening in the lab?"

---

## 6. Unified Workflow Visibility (Job #23)

**Dependencies:** Both n8n instances (MAS 188, MYCA 191)  
**Impact:** "What ran for Morgan" in one view  
**Est:** 2+ weeks  

### Scaffolding
- **Location:** Dashboard or Morgan oversight; n8n API aggregation
- **Capabilities:** List recent workflows from MAS n8n + MYCA n8n; filter by Morgan
- **API:** Proxy to both n8n instances or central log
- **Acceptance:** Single view of workflow runs across both n8ns

---

## Sprint Mapping

| Large Job | Suggested Sprint |
|-----------|------------------|
| #18 Control Plane | After Morgan panel hardening |
| #19 Worldview Digest | After EP summary usage validated |
| #20 Unified Front Door | With Cowork integration |
| #21 NatureOS Bridge | With NatureOS deployment |
| #22 MycoBrain Awareness | With telemetry bridge design |
| #23 Workflow Visibility | With n8n sync consolidation |

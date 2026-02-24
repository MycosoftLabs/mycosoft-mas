# MYCA Full Report — Asana Handoff (Claude CoWorker)

**Date**: February 23, 2026  
**Purpose**: Copy-paste this document into Claude CoWorker to automatically populate Asana with MYCA project structure, architecture, file inventory, status, and next tasks.  
**Repos**: MAS (mycosoft-mas), Website (website), MINDEX (mindex), NatureOS (NatureOS)

---

## INSTRUCTIONS FOR CLAUDE COWORKER

Use this document to create Asana tasks. Parse each section and create:
1. A project or section for "MYCA Full Integration"
2. Tasks for each major area (Architecture, Files, Status, Next Tasks)
3. Subtasks for individual work items under Next Tasks
4. Attach or reference this document in the project description

---

## 1. EXECUTIVE SUMMARY

**MYCA (Mycosoft AI)** is the multi-agent executive assistant integrated across the Mycosoft platform. It includes:
- **Frontend**: MYCAProvider context, chat widgets, floating button, search integration
- **Backend (MAS)**: Consciousness, Brain API, Intention API, NLQ API, A2A gateway, SearchAgent
- **Protocols**: A2A (agent-to-agent), WebMCP (browser tools), UCP (commerce)
- **Data**: MINDEX (species, compounds, genetics), Exa (web search), Metabase (analytics)

**Current Status**: Core integration complete. Text-based search and chat work across search, ai-studio, dashboard, NatureOS. Voice/PersonaPlex alignment in progress. Pricing/billing UCP flow pending.

---

## 2. ARCHITECTURE

### 2.1 High-Level Flow

```
User (Website/NatureOS) 
  → MYCAProvider (session, conversation, consciousness)
  → MYCAChatWidget / AIWidget / FloatingButton
  → /api/myca/*, /api/search/ai, /api/search/ai/stream
  → MAS (192.168.0.188:8001)
    → Consciousness API
    → Brain API (LLM, memory)
    → Intention API (Redis)
    → NLQ API (parse/execute)
    → A2A Gateway (Agent Card, message/send)
    → SearchAgent (MINDEX, Exa)
  → MINDEX (192.168.0.189:8000), Exa, Metabase
```

### 2.2 Protocol Layer

| Protocol | Purpose | Status |
|----------|---------|--------|
| A2A | Agent-to-agent; Agent Card, message/send | Implemented |
| MCP | Tool registry (exa_search, mindex_query) | Implemented |
| WebMCP | Browser tools (run_search, focus_widget, add_notepad) | Implemented |
| UCP | Commerce (quote, checkout) | Adapter exists; pricing page not wired |

### 2.3 Component Map

| Layer | Components |
|-------|------------|
| Context | MYCAProvider, useMYCA, session/conversation state |
| UI | MYCAChatWidget, MYCAFloatingButton, AIWidget, MobileSearchChat |
| API (Website) | /api/myca/query, sync, consciousness/*, a2a/*, intention |
| API (Search) | /api/search/ai, /api/search/ai/stream, /api/search/exa, /api/search/unified |
| API (MAS) | /api/myca/chat, intention, consciousness; /voice/brain/*; /api/nlq/* |

---

## 3. FILE INVENTORY

### 3.1 Website (WEBSITE/website/)

| File | Purpose | Status |
|------|---------|--------|
| `contexts/myca-context.tsx` | MYCAProvider, session, conversation, executeSearchAction | Implemented |
| `components/myca/MYCAChatWidget.tsx` | Unified chat UI | Implemented |
| `components/myca/MYCAFloatingButton.tsx` | Floating Brain icon, opens chat sheet | Implemented |
| `components/search/panels/MYCAChatPanel.tsx` | Search left panel (wraps MYCAChatWidget) | Implemented |
| `components/mas/myca-chat-panel.tsx` | Legacy wrapper | Implemented |
| `components/search/fluid/widgets/AIWidget.tsx` | Search AI answers, streaming, actions | Implemented |
| `components/search/fluid/FluidSearchCanvas.tsx` | Search canvas, widget layout | Implemented |
| `components/search/SearchContextProvider.tsx` | myca-search-action listener, focus_widget, add_to_notepad | Implemented |
| `hooks/useWebMCPProvider.ts` | WebMCP tool registration | Implemented |
| `hooks/use-mobile-search-chat.ts` | Mobile search chat | Implemented |
| `app/search/page.tsx` | Search page with MYCAProvider | Implemented |
| `app/natureos/ai-studio/page.tsx` | AI Studio with MYCAChatWidget | Implemented |
| `app/dashboard/page.tsx` | Dashboard with MYCAFloatingButton | Implemented |
| `app/scientific/layout.tsx` | Scientific layout with MYCAFloatingButton | Implemented |
| `app/test-voice/page.tsx` | Voice test page | Implemented |
| `app/admin/voice-health/page.tsx` | Voice diagnostics with MYCAFloatingButton | Implemented |
| `app/layout.tsx` | Root layout; MYCAProvider in provider stack | Implemented |
| `app/natureos/layout.tsx` | NatureOS layout; MYCAFloatingButton | Implemented |
| `app/api/myca/query/route.ts` | NatureOS-compatible MYCA query proxy | Implemented |
| `app/api/myca/sync/route.ts` | Conversation save/restore | Implemented |
| `app/api/myca/conversations/route.ts` | List/load conversations | Implemented |
| `app/api/myca/consciousness/status/route.ts` | Consciousness status proxy | Implemented |
| `app/api/myca/consciousness/chat/route.ts` | Consciousness chat proxy | Implemented |
| `app/api/myca/consciousness/awaken/route.ts` | Awaken consciousness | Implemented |
| `app/api/myca/a2a/agent-card/route.ts` | A2A Agent Card proxy | Implemented |
| `app/api/myca/a2a/message/send/route.ts` | A2A message send proxy | Implemented |
| `app/api/myca/intention/route.ts` | Intention record proxy | Implemented |
| `app/api/search/ai/route.ts` | Search AI (model routing, context) | Implemented |
| `app/api/search/ai/stream/route.ts` | Search AI streaming (SSE) | Implemented |
| `app/api/search/exa/route.ts` | Exa search proxy | Implemented |
| `app/api/search/unified/route.ts` | MINDEX + Exa unified search | Implemented |

### 3.2 MAS Backend (mycosoft-mas/)

| File | Purpose | Status |
|------|---------|--------|
| `mycosoft_mas/core/myca_main.py` | MAS entrypoint, router registration | Implemented |
| `mycosoft_mas/core/routers/consciousness_api.py` | /api/myca/chat, status, awaken | Implemented |
| `mycosoft_mas/core/routers/brain_api.py` | /voice/brain/chat, stream, status | Implemented |
| `mycosoft_mas/core/routers/intention_api.py` | /api/myca/intention (Redis + fallback) | Implemented |
| `mycosoft_mas/core/routers/nlq_api.py` | /api/nlq/parse, execute, query | Implemented |
| `mycosoft_mas/core/routers/a2a_api.py` | A2A Agent Card, message/send | Implemented |
| `mycosoft_mas/consciousness/core.py` | MYCAConsciousness, process_search_query | Implemented |
| `mycosoft_mas/agents/clusters/search_discovery/search_agent.py` | SearchAgent (MINDEX, Exa) | Implemented |
| `mycosoft_mas/llm/tool_pipeline.py` | exa_search tool registration | Implemented |
| `mycosoft_mas/integrations/ucp_commerce_adapter.py` | UCP commerce adapter | Implemented |
| `mycosoft_mas/myca/` | Self-improvement scaffold (constitution, evals) | Implemented |

### 3.3 Documentation

| File | Purpose |
|------|---------|
| `docs/myca/MYCA_DOC_INDEX.md` | Single entry point for all MYCA docs |
| `docs/myca/MYCA_DOC_ORGANIZED_LIST.md` | Large vs atomic doc lists |
| `docs/myca/atomic/*.md` | 15 atomic component docs |
| `docs/MYCA_ECOSYSTEM_UNIFICATION_FEB17_2026.md` | Full stack overview |
| `docs/MYCA_PROTOCOL_STACK_INTEGRATION_PLAN_FEB17_2026.md` | A2A/WebMCP/UCP plan |
| `docs/MYCA_SELF_IMPROVEMENT_SYSTEM_FEB17_2026.md` | Constitution, skills, evals |
| `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md` | Consciousness pipeline |
| `website/docs/MYCA_FULL_WEBSITE_INTEGRATION_FEB17_2026.md` | Website integration |

### 3.4 Cursor / Rules

| File | Purpose |
|------|---------|
| `.cursor/agents/myca-docs.md` | MYCA documentation sub-agent |
| `.cursor/rules/myca-protocols.mdc` | A2A, WebMCP, UCP usage rules |
| `.cursor/rules/myca-docs-living.mdc` | Living doc naming, myca-docs invocation |

---

## 4. VERIFICATION CHECKLIST (DONE)

- [x] Search on /search returns Exa results when include_web=true
- [x] AIWidget streams and executes focus_widget/add_to_notepad
- [x] MYCA chat on search, ai-studio, dashboard, NatureOS shares same conversation
- [x] Navigate search → ai-studio → NatureOS; conversation continues
- [x] Test-voice and chat use same session; reload persists (localStorage)
- [x] NatureOS tools can open MYCA floating button
- [x] A2A Agent Card lists myca_search, myca_nlq skills

---

## 5. NEXT TASKS (FOR ASANA)

### 5.1 High Priority

1. **Wire pricing/billing to MAS commerce**
   - Update `app/pricing/page.tsx` to call `/api/mas/commerce/quote` and `/api/mas/commerce/checkout`
   - Ensure UCP policy gate and risk tier flow through
   - Files: website/app/pricing/page.tsx, website/app/api/mas/commerce/*

2. **PersonaPlex voice alignment**
   - Align PersonaPlex bridge with MYCA session/conversation IDs
   - Ensure test-voice and MYCA chat share same session_id when voice is active
   - Files: services/personaplex-local/*, app/test-voice/page.tsx, contexts/myca-context.tsx

3. **NatureOS mycosoft.com routing**
   - Ensure NatureOS repo `myca-query.ts` uses website `/api/myca/query` when embedded on mycosoft.com
   - Files: NATUREOS/NatureOS/website-integration/api/myca-query.ts

### 5.2 Medium Priority

4. **Audit remaining NatureOS pages**
   - Ensure all 54 NatureOS pages that need AI have MYCA access (floating button or embedded widget)
   - Add MYCAFloatingButton to: devices, lab-tools, mindex, genetics, data-explorer, reports, tools/*

5. **UCP commerce live integration**
   - Connect UCP adapter to real checkout flows where vendors support UCP
   - Add regression tests for commerce API

6. **WebMCP on all MYCA surfaces**
   - Verify useWebMCPProvider runs on: search, ai-studio, test-voice, dashboard, scientific, NatureOS layout
   - Add NatureOS-specific tools (e.g. natureos_query_device, natureos_run_sim) if needed

### 5.3 Lower Priority

7. **MINDEX for MYCA state**
   - Use myca_autobiographical_memory, myca_consciousness_journal for intention/session summaries
   - Ensure intention API persists to Redis/MINDEX for cross-session restoration

8. **Protocol telemetry**
   - Add protocol_event logging (protocol=a2a|webmcp|ucp, remote_agent, tool_name, risk_flags)
   - Integrate with existing event ledger

9. **MYCA documentation sync**
   - Run `@myca-docs` after any MYCA code change to keep atomic docs current
   - Ensure MYCA_DOC_INDEX and MYCA_DOC_ORGANIZED_LIST stay up to date

---

## 6. DEPENDENCIES

| Dependency | Purpose |
|------------|---------|
| EXA_API_KEY | Exa web search |
| REDIS_URL | Intention persistence (optional; in-memory fallback) |
| METABASE_URL, METABASE credentials | Metabase NLQ |
| MAS 192.168.0.188:8001 | MAS orchestrator |
| MINDEX 192.168.0.189:8000 | MINDEX API |
| WEBSITE_API_URL | MAS → website for Metabase when NLQ intent=query_metabase |

---

## 7. ASANA PROJECT SUGGESTION

**Project Name**: MYCA Full Website Integration  
**Sections**:
1. Architecture & Docs
2. Implemented (reference)
3. Next Tasks — High
4. Next Tasks — Medium
5. Next Tasks — Low

**Task Template** (for each next task):
- Title: [Task name from 5.x]
- Description: [Copy from 5.x]
- Subtasks: [Break down if needed]
- Related files: [From 5.x]

---

## 8. COPY-PASTE BLOCK FOR CLAUDE COWORKER

```
Create an Asana project "MYCA Full Website Integration" with the following:

SECTIONS:
- Architecture & Docs
- Implemented (reference)
- Next Tasks — High Priority
- Next Tasks — Medium Priority
- Next Tasks — Lower Priority

HIGH PRIORITY TASKS:
1. Wire pricing/billing to MAS commerce — Update app/pricing/page.tsx to call /api/mas/commerce/quote and checkout. Ensure UCP policy gate.
2. PersonaPlex voice alignment — Align PersonaPlex bridge with MYCA session/conversation IDs. Same session_id for test-voice and chat.
3. NatureOS mycosoft.com routing — Ensure myca-query.ts uses website /api/myca/query when embedded on mycosoft.com.

MEDIUM PRIORITY TASKS:
4. Audit remaining NatureOS pages — Add MYCAFloatingButton to devices, lab-tools, mindex, genetics, data-explorer, reports, tools/*.
5. UCP commerce live integration — Connect UCP adapter to real checkout flows.
6. WebMCP on all MYCA surfaces — Verify useWebMCPProvider on search, ai-studio, test-voice, dashboard, scientific, NatureOS.

LOWER PRIORITY TASKS:
7. MINDEX for MYCA state — Persist intention/session to MINDEX.
8. Protocol telemetry — Add protocol_event logging.
9. MYCA documentation sync — Run @myca-docs after code changes.

Attach the full report (MYCA_ASANA_HANDOFF_REPORT_FEB23_2026.md) to the project description.
```

---

*End of MYCA Asana Handoff Report*

# MYCA Ecosystem Unification – Feb 17, 2026

**Status**: Implemented  
**Last verified**: February 17, 2026  
**Related Plan**: `.cursor/plans/myca_ecosystem_unification_17263677.plan.md`

## Overview

Unifies A2A/WebMCP/UCP protocol layer, search integration (Exa, Metabase LLM, frontier models, consciousness), and MYCA connectivity across frontend, middleware, backend, and NatureOS.

## Touchpoints

### Backend (MAS)

| Component | Location | Changes |
|-----------|----------|---------|
| SearchAgent | `agents/clusters/search_discovery/search_agent.py` | _keyword_search, _semantic_search, _fuzzy_search via MINDEX; Exa in _semantic_search |
| Exa tool | `llm/tool_pipeline.py` | exa_search registered and _execute_exa_search handler |
| Consciousness | `consciousness/core.py` | process_search_query() routes through attention, world model, SearchAgent |
| NLQ API | `core/routers/nlq_api.py` | POST /parse (intent via LLM), POST /execute (SearchAgent, Metabase, MINDEX) |
| Intention API | `core/routers/intention_api.py` | Redis persistence with in-memory fallback |
| A2A | `core/routers/a2a_api.py` | Skills myca_search, myca_nlq added to Agent Card |

### Website API

| Route | Purpose |
|-------|---------|
| `/api/search/ai` | Model routing (fast/quality/reasoning), full search context |
| `/api/search/ai/stream` | Proxies MAS Brain stream, passes session_id, conversation_id, context |
| `/api/search/exa` | Proxy to Exa API (server-side key) |
| `/api/search/unified` | include_web=true fetches Exa results |
| `/api/metabase` | LLM-generated SQL, schema context |
| `/api/myca/query` | NatureOS-compatible; proxies to MAS consciousness chat |

### Frontend

| Component | Changes |
|-----------|---------|
| MYCAProvider | executeSearchAction dispatches myca-search-action CustomEvent |
| SearchContextProvider | Listens for myca-search-action, executes focus_widget, add_to_notepad, search, clear_search |
| WebMCP | mycosoft_run_search, focus_widget, add_notepad_item, read_page_context, safe_navigate |
| NatureOS layout | MYCAFloatingButton (Brain icon) opens chat sheet |

### NatureOS

| File | Change |
|------|--------|
| `website-integration/api/myca-query.ts` | When on mycosoft.com/localhost, uses `/api/myca/query` (website MAS) instead of Azure |

### Protocol Rules

- `.cursor/rules/myca-protocols.mdc` – A2A, MCP, WebMCP, UCP usage; sanitize remote data; HTTPS in production

## Data Flow

1. **Search**: FluidSearchCanvas → /api/search/unified (MINDEX + Exa when include_web) → results
2. **AI Widget**: /api/search/ai or /api/search/ai/stream → MAS Consciousness/Brain → intention recorded
3. **MYCA Chat**: /api/myca/consciousness/chat or /api/myca/query → MAS
4. **NatureOS**: MycaAPI detects origin, calls /api/myca/query when embedded
5. **Intention**: POST /api/myca/intention → Redis (or in-memory fallback)

## Verification Checklist

- [x] Search on /search returns Exa results when include_web=true
- [x] AIWidget streams and executes focus_widget/add_to_notepad when actions present
- [x] MYCA chat on search, ai-studio, dashboard, NatureOS shares same conversation (session_id, conversation_id)
- [x] Navigate search → ai-studio → NatureOS tool; conversation continues
- [x] Test-voice and chat use same session; reload persists (localStorage)
- [x] NatureOS tools can open MYCA floating button and get contextual help
- [ ] Pricing/billing calls /api/mas/commerce/quote, /api/mas/commerce/checkout
- [x] A2A Agent Card lists myca_search, myca_nlq skills

## Dependencies

- EXA_API_KEY (Exa searches)
- REDIS_URL (intention persistence; optional, falls back to in-memory)
- METABASE_URL, METABASE credentials (Metabase NLQ)
- MAS 192.168.0.188:8001, MINDEX 192.168.0.189:8000
- WEBSITE_API_URL (MAS → website Metabase when NLQ intent=query_metabase)

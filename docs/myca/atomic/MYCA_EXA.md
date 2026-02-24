# MYCA Exa Integration

**Component**: Exa search API integration  
**Status**: Implemented

## Location

- `mycosoft_mas/llm/tool_pipeline.py` – exa_search tool
- `mycosoft_mas/agents/clusters/search_discovery/search_agent.py` – _semantic_search uses Exa
- `WEBSITE/website/app/api/search/exa/route.ts` – proxy

## Website Proxy

- `GET/POST /api/search/exa` – Proxies to Exa API with server-side key
- `EXA_API_KEY` required

## Unified Search

- `app/api/search/unified/route.ts` – `include_web=true` fetches Exa results alongside MINDEX

# MYCA Protocol Stack Integration Plan

**Date**: February 17, 2026  
**Author**: MYCA  
**Status**: Partially implemented — A2A server, Agent Card, WebMCP tools deployed; UCP commerce routing in progress

## Overview

This plan integrates the A2A (agent-to-agent), MCP/WebMCP (agent-to-tool + web app tools), and UCP (commerce workflow) protocols as a unified protocol-layer upgrade across the Mycosoft stack. The goal is to make MYCA interoperable with remote agents, enable structured browser tool calls on Mycosoft web apps, and support commerce flows via UCP-first routing.

## Objectives

- Expose MYCA (and key subagents) over A2A with a compliant Agent Card.
- Add an A2A client + registry so MYCA can delegate tasks to remote agents.
- Add WebMCP tools to Mycosoft web apps for stable, structured UI automation.
- Add UCP-first commerce workflow support (no UI scraping if UCP exists).
- Enforce protocol security (TLS, auth, input sanitization).

## Scope

- MAS: A2A server + client, A2A registry, tool pipeline integration, security.
- Website: WebMCP provider tools on Mycosoft pages, search/notepad hooks.
- Agent tooling: A2A tool wrapper + WebMCP detection pathway.
- Documentation + rules: protocol rule, API catalog, system registry.

## Non-goals

- Voice/PersonaPlex integration changes (explicitly out-of-scope for now).
- Implementing vendor-specific commerce flows when UCP is available.

## Architecture Summary

- **A2A**: A2A server on MAS exposes MYCA and major agents via Agent Cards and message endpoints.
- **MCP**: Internal tools remain MCP; A2A delegation exposed as a tool.
- **WebMCP**: Mycosoft web apps provide structured tools via `navigator.modelContext`.
- **UCP**: Commerce requests route to UCP endpoints first; fallback only if UCP is unavailable.

## Phase 1 — A2A Server (MAS)

1. Create `mycosoft_mas/a2a/` module:
   - A2A server app (Starlette/FastAPI integration).
   - Agent Card builder for MYCA and other flagship agents.
   - `/ .well-known /agent-card.json` handler.
2. Add auth and TLS requirements (configurable in `.env`):
   - Require HTTPS in production.
   - Define `securitySchemes` in Agent Card.
3. Add routing in MAS service start:
   - Either run as dedicated service (preferred for isolation),
     or mount on MAS as a sub-app with dedicated prefix.

Deliverables:
- A2A server app, Agent Card, `.well-known` endpoint.
- Configured auth and TLS guardrails.

## Phase 2 — A2A Client + Registry (MAS)

1. Create `mycosoft_mas/integrations/a2a_client.py`:
   - Resolve Agent Cards.
   - Send/stream messages to remote agents.
2. Add A2A registry (YAML/JSON in `config/`):
   - Allowlist agent URLs + required auth.
   - Optional per-agent capabilities metadata.
3. Add sanitization + trust boundary:
   - Treat Agent Card fields and remote content as untrusted.
   - Never inject Agent Card data into prompts without filtering.
4. Register A2A delegation as an MCP tool:
   - Tool name: `a2a_send`
   - Input schema: `agent_url`, `message`, `metadata`

Deliverables:
- A2A client wrapper + registry config.
- Tool pipeline entry to call remote agents.

## Phase 3 — WebMCP Provider (Website)

1. Add a WebMCP provider module:
   - `lib/webmcp/registerMycosoftWebMCPTools.ts`
2. Register tools on client-side layout:
   - Search actions: `search`, `focus_widget`, `add_to_notepad`.
   - Minimal, deterministic outputs (no mock data).
3. Bind tool execution to SearchContext actions:
   - Reuse `myca-search-action` event path.
4. Gate tools behind feature detection:
   - Only register if `navigator.modelContext` exists.

Deliverables:
- WebMCP tools for search + notepad.
- Client-side registration in layout.

## Phase 4 — WebMCP Consumer Path (Agents)

1. Add WebMCP detection in browser automation agent:
   - Prefer tool calls when WebMCP is present.
2. Fallback to existing DOM automation when not available.
3. Log which path was used for diagnostics.

Deliverables:
- WebMCP-first execution path with fallback.

## Phase 5 — UCP Commerce Integration

1. Add `commerce_agent` (MAS):
   - UCP-first flow for buy/order/checkout.
   - Avoid UI automation if UCP endpoint exists.
2. Add UCP integration client in MAS:
   - Configured endpoints + auth in `.env`.
   - No mock data; return “not configured” if missing.
3. Add MCP tool entry for commerce workflows:
   - Tool name: `ucp_checkout` (or similar).

Deliverables:
- Commerce agent + UCP client + tool pipeline entry.

## Phase 6 — Security + Rules + Docs

1. Add protocol rule:
   - `.cursor/rules/myca-protocols.mdc`
2. Update registries:
   - `docs/API_CATALOG_FEB04_2026.md` (A2A, NLQ, WebMCP notes).
   - `docs/SYSTEM_REGISTRY_FEB04_2026.md` (A2A server, WebMCP tools).
3. Update indexes:
   - `docs/MASTER_DOCUMENT_INDEX.md`
   - `.cursor/CURSOR_DOCS_INDEX.md`

Deliverables:
- Protocol rule + updated registries/indexes.

## Testing & Verification

- Unit tests for A2A client and server:
  - Agent Card discovery.
  - Message send/stream behavior.
- Integration tests for WebMCP:
  - Tool registration and execution path.
  - Search action event wiring.
- UCP tests (when real endpoints configured):
  - Successful checkout flow via UCP client.
  - Proper “not configured” responses when missing.

## Deployment Notes

- A2A server should run behind HTTPS.
- WebMCP tools require modern browser support; fallback to DOM automation otherwise.
- UCP endpoints must be configured before enabling commerce workflows.

## Related Documents

- `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md`
- `docs/MASTER_ARCHITECTURE_FEB09_2026.md`
- `docs/MYCA_SELF_IMPROVEMENT_SYSTEM_FEB17_2026.md`

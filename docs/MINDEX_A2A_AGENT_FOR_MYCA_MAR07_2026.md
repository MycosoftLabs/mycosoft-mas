# MINDEX A2A Agent for MYCA — March 7, 2026

**Status:** Documentation  
**Purpose:** Document how the MINDEX A2A agent supports MYCA delegation for search and stats intents.  
**Related:** `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`

---

## Overview

MINDEX exposes an A2A-compatible read-only agent interface at `{MINDEX_API_URL}/api/mindex/a2a`. MAS and MYCA can delegate MINDEX queries to this agent instead of coupling directly to MINDEX internals.

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/.well-known/agent-card.json` | GET | A2A Agent Card — capabilities, skills |
| `/v1/message/send` | POST | Handle search and stats intents |

## Skills

1. **search** — Unified search across taxa, compounds, genetics, observations, research  
2. **stats** — MINDEX database statistics and counts  

## How MYCA/MAS Uses It

### MAS MINDEXBridge

MYCA OS uses `MINDEXBridge` (`mycosoft_mas/myca/os/mindex_bridge.py`) to reach MINDEX. The bridge calls:

- MINDEX API (`http://192.168.0.189:8000`) for health, search, grounding
- Redis, PostgreSQL, Qdrant for memory when available

### A2A Delegation Path

For **A2A protocol** delegation (agent-to-agent):

1. MAS or MYCA sends an A2A `message/send` to MINDEX:
   ```
   POST {MINDEX_API_URL}/api/mindex/a2a/v1/message/send
   ```

2. MINDEX A2A agent (`mindex_api/routers/a2a_agent.py`) parses intent:
   - **Stats**: Keywords "count", "stat", "how many", "total" → returns taxon/compound/genetics counts
   - **Search**: Default → unified search across taxa, compounds, genetics

3. Returns A2A task with artifact containing text result.

### Direct API vs A2A

- **Direct API**: MAS/MYCA calls MINDEX API endpoints (unified search, grounding) for in-process flows.
- **A2A**: Use when an external A2A-compatible orchestrator needs to delegate to MINDEX without knowing MINDEX internals.

## MindexAgent Integration

The MAS `MindexAgent` should prefer:

1. **MINDEXBridge** for MYCA OS — already wired in `myca/os/core.py`
2. **A2A** when the caller is A2A-native and expects task/artifact response format

Ensure `MINDEX_API_URL` points to VM 189 (e.g. `http://192.168.0.189:8000`) in MAS and MYCA env.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API base |
| `MINDEX_A2A_ENABLED` | `true` | Enable A2A agent |

## Related

- `mindex/mindex_api/routers/a2a_agent.py` — A2A implementation  
- `mycosoft_mas/myca/os/mindex_bridge.py` — MYCA MINDEX bridge  
- `docs/API_CATALOG_FEB04_2026.md` — API catalog  

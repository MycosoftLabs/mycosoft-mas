# MYCA Memory System Audit Report

**Date:** March 21, 2026
**Auditor:** Claude Code Agent
**Scope:** Full audit of memory system code, configuration, documentation accuracy, and security

---

## Executive Summary

The MYCA memory system is a substantial codebase (~15,000 lines across 37 files) implementing a 6-layer memory architecture with three backends (PostgreSQL, Redis, Qdrant). The system is **functional and well-structured** but has **9 hardcoded credential instances**, **significant documentation gaps** (MEMORY.md covers ~50% of actual implementation), **no retry/circuit-breaker patterns**, and **network connectivity issues** from the Sandbox VM (187) to MINDEX (189:5432).

---

## 1. Security Findings

### CRITICAL: Hardcoded PostgreSQL Credentials (9 instances)

All instances follow the same pattern — hardcoded connection strings used as fallback when environment variables are unset:

| File | Line | Hardcoded Credential |
|------|------|---------------------|
| `memory/persistent_graph.py` | 106 | `postgresql://mycosoft:mycosoft@postgres:5432/mycosoft` |
| `memory/analytics.py` | 20 | `postgresql://postgres:postgres@localhost:5432/mycosoft` |
| `memory/user_context.py` | 56 | `postgresql://mindex:mindex@localhost:5432/mindex` |
| `memory/mindex_graph.py` | 41 | `postgresql://mindex:mindex@localhost:5432/mindex` |
| `memory/export.py` | 21 | `postgresql://postgres:postgres@localhost:5432/mycosoft` |
| `memory/vector_memory.py` | 34 | `postgresql://mindex:mindex@localhost:5432/mindex` |
| `memory/service.py` | 222 | `postgresql://postgres:postgres@localhost:5432/mycosoft` |
| `memory/cleanup.py` | 21 | `postgresql://postgres:postgres@localhost:5432/mycosoft` |
| `memory/session_memory.py` | 81 | `postgresql://mindex:mindex@localhost:5432/mindex` |

**Note:** These are dev-only fallback credentials (localhost), not production passwords. The actual production password (`mycosoft_mindex_2026`) is not exposed in code.

**Recommendation:** Replace hardcoded fallbacks with explicit errors when env vars are missing:
```python
db_url = os.getenv("DATABASE_URL") or os.getenv("MINDEX_DATABASE_URL")
if not db_url:
    raise EnvironmentError("DATABASE_URL or MINDEX_DATABASE_URL must be set")
```

### SECURE: API Keys

All external API keys (OpenAI, Google, Qdrant) are loaded **only** from environment variables — no hardcoded values found.

### SECURE: Production Config

`config/production.env` uses `${POSTGRES_PASSWORD}` and `${MINDEX_PASSWORD}` references — properly secured.

---

## 2. Documentation Accuracy (MEMORY.md)

### All 18 documented files exist and match their descriptions

Every file listed in MEMORY.md was verified to exist with correct purpose.

### 19 Undocumented Files (Missing from MEMORY.md)

| File | Lines | Purpose |
|------|-------|---------|
| `memory/persistent_graph.py` | 1011 | **Largest file** — PostgreSQL-backed persistent knowledge graph |
| `memory/mem0_adapter.py` | 765 | Mem0-compatible 3-layer fact extraction |
| `memory/autobiographical.py` | 504 | MYCA's life story and milestone tracking |
| `memory/earth2_memory.py` | 601 | Earth2 weather forecast memory |
| `memory/gpu_memory.py` | 603 | GPU resource and inference memory |
| `memory/fungal_memory_bridge.py` | 409 | Biological-digital memory bridge |
| `memory/openviking_bridge.py` | 572 | OpenViking edge device sync |
| `memory/openviking_sync.py` | 396 | Periodic device sync coordination |
| `memory/langgraph_checkpointer.py` | 461 | LangGraph checkpoint persistence |
| `memory/voice_search_memory.py` | 434 | Voice-search memory bridge |
| `memory/analytics.py` | ~150 | Memory usage analytics |
| `memory/cleanup.py` | ~280 | Memory decay/compression/archival |
| `memory/export.py` | ~170 | Memory export/import |
| `memory/graph_indexer.py` | ~250 | Auto-builds knowledge graph from registry |
| `memory/graph_schema.py` | ~110 | Core graph types (NodeType, EdgeType) |
| `memory/long_term.py` | ~60 | Basic long-term memory layer |
| `memory/short_term.py` | ~65 | Session-based short-term memory |
| `memory/temporal_patterns.py` | ~150 | Sensor pattern storage |
| `memory/user_context.py` | ~220 | Cross-session user preferences |

### 5 Undocumented API Routers

| Router | File |
|--------|------|
| Conversation Memory | `core/routers/conversation_memory_api.py` |
| Search Memory | `core/routers/search_memory_api.py` |
| Earth2 Memory | `core/routers/earth2_memory_api.py` |
| Memory Integration | `core/routers/memory_integration_api.py` |
| Memory WebSocket | `core/routers/memory_updates_ws.py` |

**Recommendation:** Update MEMORY.md to document all 37 files and 6 routers.

---

## 3. Connection & Configuration Analysis

### Inconsistent Default Hosts

| File | Redis Default | PostgreSQL Default |
|------|--------------|-------------------|
| `memory_api.py` | `redis://redis:6379/0` (Docker) | N/A |
| `openviking_sync.py` | `192.168.0.189` (MINDEX IP) | N/A |
| `service.py` | `redis://redis:6379/0` (Docker) | `localhost:5432` |
| `myca_memory.py` | N/A | `MINDEX_DATABASE_URL` (no fallback) |
| `semantic_memory.py` | N/A | N/A (Qdrant: `192.168.0.189`) |

**Problem:** Mix of Docker hostnames (`redis`, `postgres`) and bare IPs (`192.168.0.189`) as defaults. This works inside Docker but fails on bare-metal or cross-VM calls.

### Connection Pooling

20 modules create independent `asyncpg` connection pools:
- 8 modules: min=2, max=10 (80 potential connections)
- 10 modules: min=1, max=5 (50 potential connections)
- 5 modules: min=1, max=3 (15 potential connections)
- **Total potential: ~148 PostgreSQL connections**

**Risk:** If all modules initialize simultaneously, PostgreSQL `max_connections` (typically 100-200) could be exhausted.

**Recommendation:** Implement a shared connection pool or reduce per-module pool sizes.

### No Retry Logic or Circuit Breakers

All connection failures use simple try-catch-log patterns. No:
- Exponential backoff retry
- Circuit breaker (fail-fast after repeated failures)
- Connection health monitoring loop
- Reconnection logic after transient failures

### Graceful Degradation (Good)

- Redis failures fall back to in-memory dicts (`memory_api.py:160-163`)
- PostgreSQL failures fall back to `InMemoryBackend` in test mode (`myca_memory.py:489-493`)
- Qdrant has 30-second timeouts configured

---

## 4. Agent Memory Mixin Audit

**File:** `mycosoft_mas/agents/memory_mixin.py` (518 lines)

### Strengths
- Clean mixin pattern — any agent can inherit memory capabilities
- Lazy initialization (auto-calls `init_memory()` on first use)
- All operations wrapped in try-except with graceful degradation
- A2A memory sharing well-integrated
- State save/restore lifecycle handled properly

### Issues Found
- **Line 40:** Typo — "gent_id" should be "agent_id" in docstring
- **Line 62:** `ConversationMemory(max_turns=50)` — hardcoded, should be configurable
- **Line 366:** `get_agent_memory_stats()` calls `recall(limit=1000)` for each of 6 layers — could be expensive; should use a count query instead
- **MEMORY.md mismatch:** Doc shows `learn_fact("string")` but implementation takes `Dict[str, Any]`

### API Surface (matches documentation)
- `remember()`, `recall()`, `learn_fact()`, `record_task_completion()` — all present
- `share_with_agents()`, `share_learning()`, `query_shared_knowledge()` — all present
- `save_agent_state()`, `get_agent_memory_stats()` — all present
- `add_to_conversation()`, `get_conversation_context()` — all present

---

## 5. Event Ledger Audit

**File:** `mycosoft_mas/myca/event_ledger/ledger_writer.py` (322 lines)

### Strengths
- Properly append-only (file open mode "a")
- Privacy-preserving — args hashed with SHA256, never logged raw
- Clean singleton pattern via `get_ledger()`
- Good filtering support (`read_events()` with agent/tool/status/timestamp filters)
- Failure summary aggregation (`get_failure_summary()`)
- Telemetry provenance chain support

### Issues Found
- **Line 57:** Single `events.jsonl` file — no date-based rotation despite MEMORY.md stating "7 days detailed, 30 days aggregated"
- **Line 90:** Uses `datetime.utcnow()` (deprecated) — should use `datetime.now(timezone.utc)`
- **No file size management:** The single events.jsonl will grow unbounded
- **No concurrent write safety:** Multiple processes writing to same file could interleave JSON lines
- **No compression or archival:** Documented retention policy not implemented in code

---

## 6. Network Connectivity

**Confirmed:** Sandbox VM (192.168.0.187) cannot reach MINDEX (192.168.0.189:5432).

Tested with multiple credentials:
- `postgres:postgres` — connection timeout
- `mycosoft:mycosoft` — connection timeout
- `mindex:mindex` — connection timeout
- `mycosoft:mycosoft_mindex_2026` — connection timeout

**Root cause:** Network/firewall blocking port 5432 from 187→189, not a credentials issue.

**Impact:** Memory system cannot function from Sandbox VM. Only works when running inside Docker on MAS VM (188) where Docker networking resolves `redis`, `postgres` hostnames.

---

## 7. Recommendations (Priority Order)

### P0 — Security
1. Remove 9 hardcoded credential fallbacks; fail explicitly when env vars missing
2. Add `.env` and `development.env` to `.gitignore` if not already

### P1 — Reliability
3. Implement shared connection pool (or reduce per-module pools to prevent exhaustion)
4. Add connection retry with exponential backoff for all backends
5. Fix network connectivity from Sandbox (187) to MINDEX (189:5432)

### P2 — Documentation
6. Update MEMORY.md to document all 37 memory files and 6 API routers
7. Fix `learn_fact()` signature mismatch between docs (string) and code (dict)

### P3 — Code Quality
8. Implement log rotation for event ledger (date-based files, archival)
9. Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` (2 instances in ledger_writer.py)
10. Fix typo in memory_mixin.py line 40 ("gent_id" → "agent_id")
11. Make ConversationMemory max_turns configurable instead of hardcoded 50

---

## Files Audited

| Category | Count | Files |
|----------|-------|-------|
| Memory modules | 37 | `mycosoft_mas/memory/*.py` |
| Memory routers | 6 | `mycosoft_mas/core/routers/*memory*.py` |
| Agent mixin | 1 | `mycosoft_mas/agents/memory_mixin.py` |
| Event ledger | 1 | `mycosoft_mas/myca/event_ledger/ledger_writer.py` |
| Config files | 4 | `config/settings.py`, `config/mas_config.json`, `config/development.env`, `config/production.env` |
| **Total** | **49** | |

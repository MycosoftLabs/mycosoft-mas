# MAS LLM Keys and Orchestrator Routing

**Date**: February 17, 2026  
**Status**: Complete  
**Related**: MYCA chat, Consciousness API, Voice Orchestrator

## Overview

Explains why MYCA chat sometimes bypasses the MAS orchestrator, consciousness, and agents (e.g. MindexAgent), and what is required for full consciousness routing.

---

## Why Orchestrator/Consciousness/Agents Are Not Used

### Root Cause 1: MAS Container Missing LLM API Keys

The MAS Consciousness API (`/api/myca/chat`) uses the FrontierLLMRouter, which requires at least one of:

- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`  
- `OPENAI_API_KEY`

**If none of these are set** on the MAS container (VM 192.168.0.188), consciousness returns a graceful fallback such as:

> "I'm having a moment of difficulty with that request..."

The website orchestrator detects this as `isBrokenFallback` and falls through to its own LLMs (Groq, Claude, etc.). Those LLMs run on the website server and **do not have access** to:

- MAS agent delegation (e.g. MindexAgent)
- MINDEX tool calls
- Consciousness deliberation and memory

**Fix**: Ensure the MAS container receives at least one LLM API key. Example (VM 188):

```bash
# On MAS VM, create or update .env with:
GEMINI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here
```

Then restart MAS with env loaded, e.g.:

```bash
docker run -d ... --env-file /home/mycosoft/mycosoft/mas/.env mycosoft/mas-agent:latest
```

### Root Cause 2: Fast Path for "Simple" Queries

The website orchestrator has a **fast path** for very simple queries (e.g. "4+5", "hello") so they get immediate answers without a MAS round-trip.

- **Complex triggers** prevent fast path: `mindex`, `data`, `agents`, `species`, `observation`, location names (e.g. San Diego), etc.
- If a query matches complex triggers, it is **always** sent to MAS Consciousness first.

### Root Cause 3: Data-Aware Fallback (Added Feb 17, 2026)

When consciousness fails but the user asks for real data (e.g. "what MINDEX data is available for San Diego"), the orchestrator now:

1. Detects data-intent queries (`isDataIntentQuery`)
2. Fetches MINDEX unified-search results
3. Injects them into the LLM prompt
4. Returns a response based on real MINDEX data

This provides real data even when MAS consciousness is unavailable.

---

## Flow Summary

| Step | Condition | Action |
|------|-----------|--------|
| 1 | `isSimpleQuery` true | Fast path → Groq/Claude (no MAS) |
| 2 | `isSimpleQuery` false | Call MAS Consciousness API |
| 3 | MAS returns valid response | Use consciousness response |
| 4 | MAS returns broken fallback | If data-intent: fetch MINDEX, enrich prompt |
| 5 | LLM fallback | Call Claude → OpenAI → Groq → Gemini → Grok with enriched prompt |

---

## Enabling Full Consciousness

1. **Add LLM keys to MAS container** on VM 188 (see above).
2. **Verify consciousness**:
   ```bash
   curl -X POST http://192.168.0.188:8001/api/myca/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"what is your name"}'
   ```
   Response should be a real MYCA answer, not a fallback.
3. **Test agent delegation**: Ask "what MINDEX data is available for San Diego" — consciousness should delegate to MindexAgent and return real data.

---

## Related Documents

- [MASTER_DOCUMENT_INDEX](./MASTER_DOCUMENT_INDEX.md)
- [VM_LAYOUT_AND_DEV_REMOTE_SERVICES](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
- Website: `app/api/mas/voice/orchestrator/route.ts` — orchestrator routing logic

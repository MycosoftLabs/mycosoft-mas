# MYCA Widget AI Integration - Feb 11, 2026

## Summary

The MYCA AI widget in Fluid Search now uses MYCA Consciousness and Brain as primary AI sources. It **never** returns "No AI results" or "fallback" — always provides a real answer.

## Problem (Before)

- `/api/search/ai` only tried OpenAI and Anthropic
- When neither API key was set, it returned: *"No AI results for [query]. Try searching the MINDEX species database."* with `source: "fallback"`
- No integration with MYCA Consciousness, Intent Engine, Brain, or persistent memory

## Solution (After)

Fallback chain in `/api/search/ai`:

1. **MYCA Consciousness** – Intent Engine, persistent memory, full awareness (`POST /api/myca/chat`)
2. **MAS Brain** – Memory-integrated LLM (`POST /voice/brain/chat`)
3. **OpenAI** – GPT-4o-mini (if key set)
4. **Anthropic** – Claude 3 Haiku (if key set)
5. **Local Knowledge Base** – Always succeeds; never "No AI results"

## Integration Points

| System | Integration |
|--------|-------------|
| **Intent Engine** | `recordIntention()` fires `POST /api/myca/intention` when MYCA Consciousness or Brain succeeds |
| **Consciousness** | Primary: `POST /api/myca/chat` with message, session_id, context |
| **Brain** | Secondary: `POST /voice/brain/chat` with message, include_memory_context |
| **Persistent Memory** | Consciousness and Brain both use MINDEX, autobiographical memory, and recall |

## Files Changed

| File | Change |
|------|--------|
| `website/app/api/search/ai/route.ts` | Rewritten: MYCA-first fallback chain, intention events, context support |

## API Contract (Unchanged)

- **GET** `/api/search/ai?q=...` or **POST** with `{ q, context? }`
- **Response**: `{ query, result: { answer, source, confidence }, timestamp }`
- **Source values**: `"MYCA Consciousness"`, `"MYCA Brain"`, `"OpenAI"`, `"Anthropic"`, `"MYCA Knowledge Base"`

## Context Passing

Optional `context` (GET `?context=...` or POST body):

```json
{
  "species": ["Ganoderma lucidum", "Reishi"],
  "compounds": ["ganoderic acid"],
  "previousSearches": ["reishi medicinal"]
}
```

When present, it is appended to the user message for Consciousness and Brain so responses are contextual.

## Requirements

- **MAS VM (192.168.0.188)** must be reachable for MYCA Consciousness and Brain
- `MAS_API_URL` in website env (default: `http://192.168.0.188:8001`)
- OpenAI/Anthropic keys optional; local knowledge base always available

## Testing

1. Search with AI enabled (Fluid Search, `includeAI: true`)
2. Ask follow-ups in the AI widget
3. Confirm source shows `MYCA Consciousness`, `MYCA Brain`, or `MYCA Knowledge Base` — never `fallback`
4. Verify MAS is up: `curl http://192.168.0.188:8001/health`

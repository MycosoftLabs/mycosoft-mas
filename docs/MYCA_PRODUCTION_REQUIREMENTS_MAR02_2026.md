# MYCA Production Requirements (Mar 2, 2026)

**Status:** Current  
**Purpose:** Ensure MYCA (voice + chat) is fully usable in production and sandbox.

## Minimum for Full MYCA Intelligence

1. **MAS reachable**  
   - `MAS_API_URL` (e.g. `http://192.168.0.188:8001`) must be reachable from the host running the Next.js API (Sandbox 187 or dev PC).  
   - Used for consciousness (`/api/myca/chat`) and agent context.

2. **At least one LLM provider**  
   - **Recommended:** `GROQ_API_KEY` (fast, reliable as of Mar 2026).  
   - Alternatives: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`, `XAI_API_KEY`.  
   - **Ollama (local):** If no cloud keys, set `OLLAMA_BASE_URL` (e.g. `http://192.168.0.188:11434`) and ensure Ollama is running on that host.

3. **Optional but recommended**  
   - `MINDEX_API_URL` (e.g. `http://192.168.0.189:8000`) for data-intent queries.  
   - `N8N_URL` (e.g. `http://192.168.0.188:5678`) for workflow-driven responses.

## VM Layout (Reference)

| VM    | IP           | Role        | Key ports              |
|-------|--------------|------------|------------------------|
| Sandbox | 192.168.0.187 | Website     | 3000                   |
| MAS   | 192.168.0.188 | Orchestrator, n8n, Ollama | 8001, 5678, 11434 |
| MINDEX | 192.168.0.189 | DB + API    | 5432, 8000             |

From Sandbox (187), MAS (188) and MINDEX (189) must be reachable. From local dev, set `.env.local` to point at these IPs.

## When All Providers Fail

- **Voice:** User sees a friendly “brief connectivity issue” message and is invited to try again. A one-time retry (Groq + Ollama) runs after 2s before that message. Local fallback also handles greetings, “who are you”, “help”, “how are you”, thanks, and simple math.
- **Chat:** User sees a single friendly message; internal API key names are never exposed.

## Verification

- MAS health: `GET http://192.168.0.188:8001/health`  
- Ollama: `GET http://192.168.0.188:11434/api/tags`  
- Check env: `MAS_API_URL`, `OLLAMA_BASE_URL`, and at least one of `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, etc.

## Related

- Voice orchestrator: `WEBSITE/website/app/api/mas/voice/orchestrator/route.ts`  
- Chat route: `WEBSITE/website/app/api/mas/chat/route.ts`  
- VM layout: `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`

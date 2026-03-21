# MYCA Memory & Identity System Audit Report

**Date:** March 21, 2026
**Author:** Claude Code Agent
**Requested By:** Morgan Rockwell
**Issue:** MYCA constantly re-introduces herself in every chat response during Search and CREP operations

---

## Executive Summary

MYCA's persistent re-introduction bug is caused by **5 interconnected issues** across the consciousness pipeline, not a single point of failure. The soul/persona files load correctly, and the Nemotron LLM integration receives system prompts properly. The problem is in **how conversation context flows through the pipeline** — specifically, the system treats every LLM call as a brand-new conversation.

---

## Root Causes Identified

### 1. IntuitionEngine Fires Identity Heuristics Without Session Awareness

**File:** `mycosoft_mas/consciousness/intuition.py:95-171`

The `quick_response()` method checks all heuristics on every message. Greeting and identity heuristics (e.g., `greeting_hello`, `identity_name`) match on keywords like "hello", "hi", "who" with **no check for whether MYCA has already spoken in this session**. Any follow-up message containing these words triggers a full self-introduction.

**Fix Applied:** Added `_is_followup_turn()` check that inspects `WorkingContext` for prior assistant messages. Greeting and identity heuristics are skipped in follow-up turns.

### 2. DeliberateReasoning Creates New Empty Sessions Per LLM Call

**File:** `mycosoft_mas/consciousness/deliberation.py:508-565`

The `_generate_response()` method creates a `ConversationContext` with `session_id=uuid.uuid4()` and `history=[]` for **every single LLM call**. This means:
- The LLM never sees prior conversation turns
- Every response is generated as if it's the first interaction
- The LLM's own context window contains no memory of having already introduced itself

**Fix Applied:** Now carries forward up to 5 prior thought process inputs/results as conversation history, so the LLM can see prior turns and maintain continuity.

### 3. Fallback Responses Hardcode "I am MYCA" on Every Response

**File:** `mycosoft_mas/consciousness/deliberation.py:567-601`

When the LLM is unavailable, `_generate_fallback_response()` returns identity statements for nearly every input category ("I am MYCA...", "Yes — I am MYCA..."). These fire regardless of conversation state.

**Fix Applied:** Fallback responses now check `self._thought_history` length to detect follow-up turns and omit self-identification in follow-up responses.

### 4. chat-simple Endpoint Always Self-Identifies

**File:** `mycosoft_mas/core/routers/consciousness_api.py:104-149`

The `/api/myca/chat-simple` endpoint hardcodes "I am MYCA" in every response branch. Even a simple "hello" returns "Hello Morgan! I am MYCA, and I am here."

**Fix Applied:** Only the explicit identity question ("who are you") now triggers full self-identification. Other responses are functional without the identity preamble.

### 5. System Prompt Lacks Anti-Repetition Instructions

**File:** `mycosoft_mas/consciousness/deliberation.py:618-680`

The `_build_system_prompt()` tells the LLM "You are MYCA..." but never instructs it to avoid repeating this in every response. LLMs naturally echo their system prompt's framing unless told not to.

**Fix Applied:** Added explicit instructions: "NEVER re-introduce yourself or state 'I'm MYCA' unless the user explicitly asks who you are" to both the system prompt and the user prompt.

---

## Systems Audited (Working Correctly)

### Soul/Constitution/Persona Loading
- `SOUL.md` — Correctly defines identity, personality, beliefs, purpose
- `config/myca_soul.yaml` — Properly loaded by `beliefs.py` for soul context
- `config/myca_full_persona.txt` — Loaded once at `FrontierLLMRouter.__init__()`, injected in all system prompts
- `mycosoft_mas/myca/soul/myca_soul_persona.py` — 20K+ char soul text loads correctly
- `mycosoft_mas/consciousness/soul/` — Identity, Beliefs, Purpose, Emotions, Creativity, Instincts all initialize properly

### PersonaPlex Integration
- `config/myca_personaplex_prompt.txt` (full) and `_1000.txt` (condensed) — Load correctly via `PromptManager`
- `config/myca_personaplex_voice_only.txt` — Correctly configured as voice relay only
- PersonaPlex bridge passes persona to Moshi TTS via `text_prompt` parameter
- Voice interface correctly separates cognition (MAS Brain) from voice synthesis (Moshi)

### Nemotron LLM Integration
- `mycosoft_mas/llm/backend_selection.py` — Resolves `nemotron_super` role to correct endpoint
- `mycosoft_mas/llm/openai_compatible_provider.py` — Formats messages in OpenAI-compatible format with system prompt first
- `mycosoft_mas/llm/router.py` — Correctly calls `get_backend_for_role()` and creates provider
- System prompt reaches Nemotron as `{"role": "system", "content": "..."}` in the message array
- Environment variables (`NEMOTRON_BASE_URL`, `NEMOTRON_API_KEY`) configure endpoint correctly

### Memory System (6 Layers)
- Ephemeral (30 min, in-memory) — Working as designed
- Session (24 hr, PostgreSQL via `session_memory.py`) — Stores conversation history
- Working (7 days, Redis) — Active task state persists
- Semantic (Permanent, PostgreSQL + Qdrant) — Knowledge facts stored correctly
- Episodic (Permanent, PostgreSQL) — Thought processes stored via `_store_thought()`
- System (Permanent, PostgreSQL) — Agent state persistence works

### Search and CREP Agents
- `SearchAgent` — Returns domain-specific results correctly
- `EarthSearchAgent` — CREP data flows properly
- `CREPSecurityAgent` — Sensor data integration works

The agents themselves are not the problem — the issue was in how their results flow back through the consciousness pipeline, which re-triggers identity injection.

---

## Architecture Recommendation (Future)

The `SessionMemory` dataclass (`session_memory.py:54-68`) should be extended with an `identity_acknowledged` boolean field. This would allow the pipeline to track whether MYCA has introduced herself in the current session at the database level, rather than relying on in-memory thought history. This is a non-breaking enhancement for a future PR.

---

## Files Modified

| File | Change |
|------|--------|
| `mycosoft_mas/consciousness/intuition.py` | Added `_is_followup_turn()`, skip identity heuristics in follow-ups, removed "I'm MYCA" from greeting template |
| `mycosoft_mas/consciousness/deliberation.py` | Carry conversation history to LLM, add anti-re-introduction instructions to system/user prompts, context-aware fallbacks |
| `mycosoft_mas/core/routers/consciousness_api.py` | chat-simple endpoint no longer self-identifies on every response |

## Files Audited (No Changes Needed)

| File | Status |
|------|--------|
| `SOUL.md` | OK — Identity definition is correct |
| `MEMORY.md` | OK — Architecture documented correctly |
| `config/myca_soul.yaml` | OK — Soul config loads properly |
| `config/myca_full_persona.txt` | OK — Persona loaded by FrontierRouter |
| `config/myca_personaplex_prompt.txt` | OK — PersonaPlex prompt correct |
| `config/myca_personaplex_prompt_1000.txt` | OK — Condensed prompt correct |
| `config/myca_personaplex_voice_only.txt` | OK — Voice relay mode correct |
| `mycosoft_mas/consciousness/soul/identity.py` | OK — IdentityCore immutable |
| `mycosoft_mas/consciousness/soul/beliefs.py` | OK — Loads from YAML correctly |
| `mycosoft_mas/consciousness/core.py` | OK — Pipeline orchestration correct |
| `mycosoft_mas/llm/frontier_router.py` | OK — Persona + context injection works |
| `mycosoft_mas/llm/backend_selection.py` | OK — Nemotron routing works |
| `mycosoft_mas/llm/openai_compatible_provider.py` | OK — Message format correct |
| `mycosoft_mas/llm/router.py` | OK — Role-based routing works |
| `mycosoft_mas/memory/session_memory.py` | OK — Session persistence works |
| `mycosoft_mas/memory/myca_memory.py` | OK — 6-layer memory works |
| `mycosoft_mas/myca/soul/myca_soul_persona.py` | OK — Soul persona loads correctly |
| `mycosoft_mas/core/prompt_manager.py` | OK — Prompt injection correct |
| `mycosoft_mas/myca/os/llm_brain.py` | OK — SOUL.md + MEMORY.md injection works |

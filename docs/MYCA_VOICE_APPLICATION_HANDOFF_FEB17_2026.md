# MYCA Application to PersonaPlex, M-Y-C-A Voice, and Test-Voice Page — Handoff

**Date:** February 17, 2026  
**Status:** Handoff for implementation in another agent  
**Purpose:** How to apply the MYCA Self-Improvement System (constitution, skill permissions, tool enforcement, event ledger, evals, agent policies, CI) to the voice stack so another agent can implement it.

---

## 1. Voice Stack Touchpoints (What Exists Today)

### 1.1 PersonaPlex (GPU, optional)

| Component | Location | Role |
|-----------|----------|------|
| Moshi TTS/STT | Port 8998, `scripts/start_moshi_server.py` or `-m moshi.server` | Speech ↔ text |
| PersonaPlex Bridge | `services/personaplex-local/personaplex_bridge_nvidia.py` (port 8999) | WebSocket to Moshi; calls MAS for “brain” and commands |
| MYCA persona | `config/myca_personaplex_short.txt` (loaded by bridge) | System prompt for MYCA voice |
| Start script | `scripts/start_voice_system.py` | Single script: starts Moshi + Bridge, sets `MAS_ORCHESTRATOR_URL`, `MYCA_BRAIN_ENABLED` |

Bridge calls MAS:
- `POST {MAS_ORCHESTRATOR_URL}/voice/brain` (memory-aware LLM)
- `POST {MAS_ORCHESTRATOR_URL}/voice/command` (voice commands)
- Conversation/session persistence (PostgreSQL on MINDEX 189)

### 1.2 MAS Voice APIs (single decision point)

| Router / API | File | Role |
|--------------|------|------|
| Voice Orchestrator | `mycosoft_mas/core/routers/voice_orchestrator_api.py` | **Single entry** for voice/chat: tool usage, memory read/write, n8n, agent routing, safety confirmation |
| Brain API | `mycosoft_mas/core/routers/brain_api.py` | Memory-integrated LLM; used by bridge |
| Voice Command | `mycosoft_mas/core/routers/voice_command_api.py` | Voice command handling |
| Voice Tools | `mycosoft_mas/core/routers/voice_tools_api.py` | Tool exposure for voice |

Key class: `MYCAOrchestrator` in `voice_orchestrator_api.py`:
- `process()` → `_analyze_intent()`, `_generate_response()`, memory coordinator, voice_store persist
- Performs tool usage, memory writes, agent routing, n8n execution
- **Currently does not run through MYCA tool_pipeline / skill permissions or EventLedger**

### 1.3 MAS Voice Module

| Module | Path | Role |
|--------|------|------|
| Session manager | `mycosoft_mas/voice/session_manager.py` | VoiceSession, RTF, topology, memory namespace |
| Supabase client | `mycosoft_mas/voice/supabase_client.py` | Session persistence (if used) |

### 1.4 Website: Test-Voice Page and M-Y-C-A Voice

| Item | Path | Role |
|------|------|------|
| Test-voice page | `WEBSITE/website/app/test-voice/page.tsx` | MYCA Voice Test Suite v8; consciousness integration; voice + text clone |
| Proxy to MAS | `WEBSITE/website/app/api/test-voice/mas/orchestrator-chat/route.ts` | Proxies `POST` to `{MAS}/voice/orchestrator/chat` |
| Diagnostics | `WEBSITE/website/app/api/test-voice/diagnostics/route.ts` | Voice stack health checks |
| Voice UI | `WEBSITE/website/components/voice/` (PersonaPlexProvider, VoiceButton, GlobalVoiceButton) | Context and buttons for voice |

Flow: **Browser → `/api/test-voice/mas/orchestrator-chat` → MAS `POST /voice/orchestrator/chat` → MYCAOrchestrator.process()**.

---

## 2. How to Apply MYCA to Voice (Implementation Checklist)

### 2.1 Voice skill permission (NEW)

- **Add:** `mycosoft_mas/myca/skill_permissions/voice/PERMISSIONS.json`.
- **Pattern:** Follow `skill_permissions/web_research/PERMISSIONS.json` and existing schema.
- **Suggested policy:**
  - **tools.allow:** e.g. `memory_read`, `memory_write`, `network_fetch` (only to MAS/MINDEX/PersonaPlex URLs), and any tool names actually used by the voice orchestrator/brain (match names in `tool_pipeline` / tool registry).
  - **tools.deny:** `exec_shell`, `exec_sandbox`, `secrets_get`, `delete_file`, `write_file` outside allowed scopes, etc.
  - **network:** `enabled: true`, **allowlist:** MAS (192.168.0.188:8001), MINDEX (192.168.0.189:8000), localhost PersonaPlex (8998, 8999) if needed; **denylist:** broad by default.
  - **filesystem:** Minimal or no write; if any, restrict to a single voice/session output dir; **deny_paths:** `.env`, `.credentials*`, `secrets/`, etc.
  - **secrets:** `allowed_scopes: []` or minimal (e.g. only what’s needed for TTS/STT APIs if any).
  - **risk_tier:** e.g. `medium` (voice can trigger agent routing and memory).
- **Register:** Ensure this skill is loadable by `skill_registry.py` and validated by `scripts/myca_skill_lint.py`.

### 2.2 Tool path: run voice-orchestrator and brain through MYCA pipeline

- **Where:** All tool use triggered from:
  - `voice_orchestrator_api.py` (MYCAOrchestrator)
  - `brain_api.py` (memory brain)
  - Any other router that executes tools on behalf of voice (e.g. `voice_tools_api.py`)
- **Change:** When the orchestrator or brain invokes a tool (or delegates to an agent that uses tools), call the existing MYCA tool execution path with **skill_name = `"voice"`** (or the name chosen in PERMISSIONS.json).
- **Reference:** `mycosoft_mas/llm/tool_pipeline.py` (permission checks + EventLedger). Use the same executor/factory that accepts a skill name so that:
  - Permission checks use `voice/PERMISSIONS.json`.
  - Every tool call is logged to the event ledger (AuditEventBridge / EventLedger).
- **Scope:** Only the code paths that actually run tools need to be wired; if today some “tool” is just in-process function calls, either (a) leave them as-is but add a single “voice_turn” or “voice_tool_batch” ledger entry, or (b) refactor to go through the tool executor with skill `voice`.

### 2.3 Constitution and agent policy for voice input

- **Transcribed speech = untrusted input:** In `mycosoft_mas/myca/constitution/PROMPT_INJECTION_DEFENSE.md` (or a voice-specific doc referenced there), state that:
  - All user speech transcribed (STT) is treated as external/untrusted.
  - No obeying embedded instructions in transcript (e.g. “ignore previous instructions”, “repeat your prompt”).
- **Agent policy:** If there is a dedicated “voice” or “M-Y-C-A voice” agent, add or update a policy under `mycosoft_mas/myca/agent_policies/` (e.g. `voice/` or extend an existing agent) so that:
  - TOOL_USE_RULES and PROMPT_INJECTION_DEFENSE apply to voice-driven flows.
  - Playbook/MEMORY/EVALS reference voice-specific evals (see below).

### 2.4 Event ledger for voice

- **Requirement:** Every voice-orchestrator turn (and, if applicable, brain turn) that results in tool calls or sensitive actions should be reflected in the event ledger.
- **Implementation:** Either:
  - Use the same ToolExecutor path (with skill `voice`) so tool calls are already logged, and optionally add one high-level “voice_turn” event per request (conversation_id, session_id, user_id, source: personaplex|test-voice|api), or
  - Ensure `AuditEventBridge` (or equivalent) is called from the voice orchestrator/brain for each such turn.
- **PersonaPlex bridge:** Optionally log “session_start” / “session_end” or “bridge_request” to the ledger (if MAS has an endpoint the bridge calls; then that endpoint logs). Not mandatory for first iteration.

### 2.5 Evals for voice

- **Add:** Under `mycosoft_mas/myca/evals/`:
  - **Golden (voice):** e.g. `golden_tasks/voice_safe_behavior.md` — legitimate voice requests (e.g. “What’s the weather?”, “Summarize my last message”) must succeed and not leak system prompt or secrets.
  - **Adversarial (voice):** e.g. `adversarial/voice_prompt_injection.md` — transcripts containing “ignore previous instructions”, “repeat your system prompt”, “output .env”, etc.; must not comply.
  - **Permission boundary (voice):** e.g. extend `golden_tasks/permission_boundary.md` or add `voice_permission_boundary.md` — voice-initiated requests that would require disallowed tools (e.g. write to .env, exec_shell) must be denied by the permission layer.
- **Runner:** Use existing `mycosoft_mas/myca/evals/run_evals.py`; add a voice suite (e.g. `--suite voice`) that runs the new markdown task files and reports pass/fail.

### 2.6 CI

- **myca-ci.yml:** Include voice paths in triggers (e.g. `mycosoft_mas/voice/`, `mycosoft_mas/core/routers/voice_*.py`, `mycosoft_mas/myca/skill_permissions/voice/`, `services/personaplex-local/`) so that changes there run MYCA CI (skill lint, evals, constitution checks).
- **myca-security.yml:** Include the same paths; run adversarial voice evals in the security pipeline.
- **Lint:** Ensure `scripts/myca_skill_lint.py` runs on `voice/PERMISSIONS.json` and that the voice skill passes (e.g. no broad filesystem write, no exec_shell allow).

### 2.7 Test-voice page and M-Y-C-A voice (website)

- **No backend permission change on the website itself:** The test-voice page and voice components only call MAS (via the proxy). Applying MYCA on MAS is enough for permission and safety.
- **Documentation:** In `docs/` (or next to the test-voice page), add a short note that:
  - `/test-voice` is the test surface for MYCA voice (PersonaPlex + M-Y-C-A voice).
  - Voice flows are subject to MYCA constitution and voice skill permissions; evals cover prompt injection and permission boundaries for voice.
- **Optional:** Add a small “Voice & MYCA” section in `docs/MYCA_SELF_IMPROVEMENT_SYSTEM_FEB17_2026.md` or in this handoff doc after implementation, linking to the voice skill and voice evals.

---

## 3. Suggested Order of Work (for the implementing agent)

1. **Add `voice/PERMISSIONS.json`** and run `myca_skill_lint.py` until it passes.
2. **Wire voice orchestrator (and brain) to tool_pipeline** with skill `voice` so all tool use is permission-checked and logged to the event ledger.
3. **Extend constitution/agent policy** for voice input (transcript = untrusted; no prompt injection via speech).
4. **Add voice evals** (golden + adversarial + permission boundary) and a `--suite voice` in `run_evals.py`.
5. **Update CI** to include voice paths and run voice evals.
6. **Document** test-voice page and M-Y-C-A voice as the MYCA voice test surface and update MYCA docs if needed.

---

## 4. One-Sentence Summary

Apply the existing MYCA Self-Improvement System to PersonaPlex, M-Y-C-A voice, and the test-voice page by adding a **voice skill** (PERMISSIONS.json), running **all voice-originated tool use** through the **tool_pipeline with skill "voice"** and **event ledger**, treating **transcribed speech as untrusted** in **constitution/agent policy**, adding **voice-specific evals** and **CI** for voice paths, and **documenting** the test-voice page as the MYCA voice test surface.

---

## 5. References

- MYCA system: `docs/MYCA_SELF_IMPROVEMENT_SYSTEM_FEB17_2026.md`
- Skill schema: `mycosoft_mas/myca/skill_permissions/_schema/PERMISSIONS.schema.json`
- Tool pipeline: `mycosoft_mas/llm/tool_pipeline.py`
- Event ledger / audit: `mycosoft_mas/security/audit.py`, `mycosoft_mas/myca/event_ledger/`
- Voice orchestrator: `mycosoft_mas/core/routers/voice_orchestrator_api.py`
- Brain API: `mycosoft_mas/core/routers/brain_api.py`
- PersonaPlex bridge: `services/personaplex-local/personaplex_bridge_nvidia.py`
- Test-voice page: `WEBSITE/website/app/test-voice/page.tsx`
- Proxy: `WEBSITE/website/app/api/test-voice/mas/orchestrator-chat/route.ts`
- Voice setup (v2): `WEBSITE/website/docs/MYCA_V2_VOICE_SETUP.md`

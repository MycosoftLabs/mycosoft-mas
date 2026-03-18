# MYCA2 PSILO Full-Stack — Implementation Complete (Mar 17, 2026)

**Status:** Complete (sandbox path)  
**Related:** Plasticity Forge Phase 1 (`PLASTICITY_FORGE_PHASE1_COMPLETE_MAR14_2026.md`), plan `myca2_psilo_stack` (not edited).

## Summary

Implemented a **separate MYCA2 sandbox runtime** with PSILO session persistence in MINDEX, registry-first **backend selection for `myca2_*` aliases**, packet-first **PSILO overlay** on the executive → LLM path, **production alias promotion/rollback gates**, **mutation/lineage logging** on branch, MAS **PSILO operator API**, and **NatureOS AI Studio** topology-side widget.

## Verification

1. **Apply MINDEX migration** `migrations/0023_myca2_psilo_registry.sql` on VM 189 (or local Postgres).
2. **PSILO session:** `POST {MAS}/api/plasticity/psilo/session/start` → `session_id`; `GET .../psilo/session/{id}` shows `overlay_edges`, `metrics`.
3. **MYCA2 executive turn:** Send orchestrator message with `myca2: true`, `psilo_session_id`, `content` — response uses `myca2_core` backend (registry if alias `myca2_core` maps to candidate with `artifact_uri`).
4. **Production isolation:** `POST /api/plasticity/promote` with `alias=myca_core` **fails** unless `MYCA_ALLOW_PRODUCTION_PLASTICITY_PROMOTE=1`. Use `myca2_core` / `myca2_edge` for sandbox promotions.
5. **Rollback audit:** Rollback writes `plasticity.rollback_event` (when migration applied).
6. **UI:** NatureOS → AI Studio → **Topology** tab → **MYCA2 PSILO** panel (live MAS proxy).

## Key Files

| Area | Path |
|------|------|
| MYCA2 runtime | `mycosoft_mas/myca2/runtime.py`, `psilo_overlay.py` |
| PSILO protocol | `mycosoft_mas/psilo/protocol.py` |
| Backend selection | `mycosoft_mas/llm/backend_selection.py` (`myca2_*` registry-first) |
| Promotion gates | `mycosoft_mas/plasticity/promotion_controller.py` |
| Executive overlay | `mycosoft_mas/myca/os/executive.py`, `llm_brain.py` (`model_role`) |
| MAS PSILO API | `mycosoft_mas/core/routers/plasticity_api.py` |
| Registry client | `mycosoft_mas/integrations/plasticity_registry.py` |
| MINDEX migration | `MINDEX/mindex/migrations/0023_myca2_psilo_registry.sql` |
| MINDEX API | `mindex_api/routers/plasticity_router.py` (PSILO + lineage + alias_history) |
| Models YAML | `config/models.yaml` (`myca2_core`, `myca2_edge`, `myca2_sandbox`, `psilo_overlay`) |
| Website | `app/api/mas/myca2-psilo/**`, `components/myca2/Myca2PsiloPanel.tsx`, `app/natureos/ai-studio/page.tsx` |

## Follow-ups

- Wire **orchestrator inbound** to accept `myca2` + `psilo_session_id` from website chat or n8n.
- Run **eval case results** pipeline to `plasticity.eval_case_result` from `run_evals`.
- Optional: dedicated **sandbox Nemotron** URL via registry-only (no YAML overlap).
